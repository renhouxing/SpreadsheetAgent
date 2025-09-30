import os
import argparse

from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.utils import load_jsonl
from core.extractor import EXTRACTOR

repo_dir = os.path.abspath(os.path.dirname(__file__))

def get_files_spreadsheet():
    data = load_jsonl("data/spreadsheet.json")

    outs = []
    for d in data:
        real_dir = os.path.join(repo_dir, 'data/spreadsheet', str(d['id']))
        outs.append(dict(
            input_file=f"1_{d['id']}_input.xlsx",
            real_dir=real_dir,
            mount_dir={real_dir: "/mnt/data"}
        ))
        
    return outs

def get_files_realhit():
    outs = []

    real_dir = os.path.join(repo_dir, 'data/realhit')
    for file in os.listdir("data/realhit"):
        if not file.endswith('.xlsx'):
            continue

        outs.append(dict(
            input_file=file,
            real_dir=real_dir,
            mount_dir={real_dir: "/mnt/data"}
        ))

    return outs

def get_structure():

    data = globals()[f"get_files_{args.dataset}"]()

    extractor = EXTRACTOR[args.extractor](**args.__dict__)

    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = {executor.submit(extractor, d): i for i, d in enumerate(data)}
        for _ in tqdm(as_completed(futures), total=len(data), desc='Extracting structures'):
            pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument('--url', type=str, default=None)
    parser.add_argument('--vision_url', type=str, default=None)

    parser.add_argument('--excel2image_url', type=str, default="localhost:8007")
    parser.add_argument('--code_exec_url', type=str, default="localhost:8081")

    parser.add_argument('--top_p', type=float, default=1.0)
    parser.add_argument('--temperature', type=float, default=0)

    parser.add_argument('-f', '--force', action='store_true')

    parser.add_argument('-e', '--extractor', type=str, default='yaml_desc_verify', choices=list(EXTRACTOR.keys()))
    parser.add_argument('-d', '--dataset', type=str, default="spreadsheet", choices=['spreadsheet', 'realhit'])

    parser.add_argument('-s', '--suffix', type=str, default='debug')

    args = parser.parse_args()

    import warnings
    warnings.filterwarnings("ignore")

    if args.suffix:
        args.suffix = f"_{args.suffix}"
    args.suffix = f"{args.extractor}" + args.suffix
    if args.top_p != 1.0 or args.temperature != 0:
        args.suffix += f"_{args.top_p}_{args.temperature}"

    get_structure()
