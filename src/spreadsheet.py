import os
import argparse

from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.utils import load_jsonl, save_jsonl
from core.solver.spreadsheet import SpreadSheetSolver

repo_dir = os.path.abspath(os.path.dirname(__file__))

def get_dataset(output_dir):
    data = load_jsonl(f"data/spreadsheet.json")

    outs = []
    for d in data:
        real_dir = os.path.join(repo_dir, 'data/spreadsheet', str(d['id']))
        d.update(dict(
            input_file=f"1_{d['id']}_input.xlsx",
            output_file=f"1_{d['id']}_output.xlsx",
            real_dir=real_dir,
            mount_dir={real_dir: "/mnt/data/input", output_dir: "/mnt/data/output"},
        ))
        outs.append(d)

    return outs

def solution():

    out_dir = os.path.join(repo_dir, 'outs', args.suffix)

    file_dir = os.path.join(out_dir, 'spreadsheet')
    if os.path.exists(file_dir):
        os.system(f"rm -rf {file_dir}")
    os.makedirs(file_dir, exist_ok=True)
    os.chmod(file_dir, 0o777)

    data = get_dataset(file_dir)

    solver = SpreadSheetSolver(**args.__dict__)

    outs, eval_messages = [None] * len(data), [None] * len(data)
    soft_acc, hard_acc = 0, 0
    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = {executor.submit(solver, d): i for i, d in enumerate(data)}
        for i, future in tqdm(enumerate(as_completed(futures), start=1), total=len(data), desc='Solving'):
            result = future.result()
            outs[futures[future]] = result
    
            soft_acc += result.get('total_soft_restriction', 0)
            hard_acc += result.get('total_hard_restriction', 0)

            eval_messages[futures[future]] = {
                k: result.get(k, None) for k in [
                    'id', 'instruction', 'spreadsheet_path', 'instruction_type', 'answer_position', 
                    'test_case_results', 'test_case_messages', 'total_soft_restriction', 'total_hard_restriction'
                ]
            }

            if i % 10 == 0 or i == len(data):
                tqdm.write(f"[{i}/{len(data)}] Current Average Soft Acc: {soft_acc / i:.4f}, Hard Acc: {hard_acc / i:.4f}")

    scores = dict(soft_cell=[], soft_sheet=[], soft_all=[], hard_cell=[], hard_sheet=[], hard_all=[])
    for d in data:
        if 'Sheet' in d['instruction_type']:
            scores['soft_sheet'].append(d['total_soft_restriction'])
            scores['hard_sheet'].append(d['total_hard_restriction'])
        else:
            scores['soft_cell'].append(d['total_soft_restriction'])
            scores['hard_cell'].append(d['total_hard_restriction'])
        scores['soft_all'].append(d['total_soft_restriction'])
        scores['hard_all'].append(d['total_hard_restriction'])
    scores = {k: round(sum(v) / len(v), 4) for k, v in scores.items()}

    save_jsonl(outs, os.path.join(out_dir, f'spreadsheet.jsonl'))
    save_jsonl(eval_messages, os.path.join(out_dir, f'spreadsheet_eval.json'))
    save_jsonl(scores, os.path.join(out_dir, f'spreadsheet_accuracy.json'))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument('--url', type=str, default=None)
    parser.add_argument('--code_exec_url', type=str, default="localhost:8081")

    parser.add_argument('--top_p', type=float, default=1.0)
    parser.add_argument('--temperature', type=float, default=0)

    parser.add_argument('-e', '--extractor', type=str, default='yaml_desc_verify')

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
