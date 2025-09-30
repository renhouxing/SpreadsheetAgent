import os
import argparse

from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.utils import load_jsonl, save_jsonl
from core.solver.realhit import RealHiTSolver

repo_dir = os.path.abspath(os.path.dirname(__file__))

def get_dataset():
    data = load_jsonl("data/rs.json")

    outs = []
    for d in data['queries']:
        real_dir = os.path.join(repo_dir, 'data/realhit')
        d.update(dict(
            real_dir=real_dir,
            mount_dir={real_dir: "/mnt/data/input"},
        ))
        outs.append(d)
    
    return outs

def solution():
    data = get_dataset()

    os.makedirs(f"outs/{args.suffix}", exist_ok=True)

    solver = RealHiTSolver(**args.__dict__)

    scores = {
        "Fact Checking": {"F1": [], "EM": []},
        "Numerical Reasoning": {"F1": [], "EM": []},
        "Structure Comprehending": {"F1": [], "EM": []},
    }

    outs, eval_results = [None] * len(data), [None] * len(data)
    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = {executor.submit(solver, d): i for i, d in enumerate(data)}
        for i, future in tqdm(enumerate(as_completed(futures), start=1), total=len(data), desc='Solving'):
            result = future.result()
            outs[futures[future]] = result

            eval_results[futures[future]] = {
                k: result.get(k, None) for k in [
                    'id', 'Question', 'QuestionType', 'eval'
                ]
            }

            for k in scores[result['QuestionType']]:
                scores[result['QuestionType']][k].append(result['eval'][k])

            if i % 100 == 0 or i == len(data):
                for k_1 in scores:
                    for k_2 in scores[k_1]:
                        s = sum([s for s in scores[k_1][k_2] if s is not None]) / len(scores[k_1][k_2]) if len(scores[k_1][k_2]) > 0 else 0.0
                        tqdm.write(f"{k_1} {k_2}: {s:.4f}")
                
    for k_1 in scores:
        for k_2 in scores[k_1]:
            scores[k_1][k_2] = sum([s for s in scores[k_1][k_2] if s is not None]) / len(scores[k_1][k_2]) if len(scores[k_1][k_2]) > 0 else 0.0
    
    save_jsonl(outs, f"outs/{args.suffix}/realhit.jsonl")
    save_jsonl(scores, f"outs/{args.suffix}/realhit_score.json")
    save_jsonl(eval_results, f"outs/{args.suffix}/realhit_eval.json")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument('--url', type=str, default=None)
    parser.add_argument('--code_exec_url', type=str, default="localhost:8081")

    parser.add_argument('--top_p', type=float, default=1.0)
    parser.add_argument('--temperature', type=float, default=0)

    parser.add_argument('-e', '--extractor', type=str, default='tree')

    parser.add_argument('-p', '--use_python_tool', action='store_true')

    parser.add_argument('-s', '--suffix', type=str, default='debug')

    args = parser.parse_args()

    import warnings
    warnings.filterwarnings("ignore")

    if args.suffix:
        args.suffix = f"_{args.suffix}"
    args.suffix = f"{args.extractor or 'base'}" + args.suffix
    
    if args.top_p != 1.0 or args.temperature != 0:
        args.suffix += f"_{args.top_p}_{args.temperature}"

    solution()
