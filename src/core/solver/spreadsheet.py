import os
import json
import traceback
import pandas as pd

from ..utils import tool_call_resp, model_resp, python_tool, convert_excel_to_latex_tool, vision_question_answer_tool
from ..client import ClientJupyterKernel, extract_code

from ..eval.spreadsheet import run_solution_one_data

FIRST_ROUND_PROMPT = """You are a spreadsheet expert who can manipulate spreadsheets through Python code.

You need to solve the given spreadsheet manipulation question, which contains six types of information:
- instruction: The question about spreadsheet manipulation.
- spreadsheet_path: The path of the spreadsheet file you need to manipulate.
- spreadsheet_content: The first few rows of the content of speadsheet file.
- spreadsheet_information: The hierarchical structure of the spreadsheet. It contains information about the row and column headers, including their levels, start and end positions, and values.
- instruction_type: There are two values (Cell-Level Manipulation, Sheet-Level Manipulation) used to indicate whether the answer to this question applies only to specific cells or to the entire worksheet.
- answer_position: The position need to be modified or filled. For Cell-Level Manipulation questions, this field is filled with the cell position; for Sheet-Level Manipulation, it is the maximum range of cells you need to modify. You only need to modify or fill in values within the cell range specified by answer_position.
- output_path: You need to generate the modified spreadsheet file in this new path.

Below is the spreadsheet manipulation question you need to solve:
### instruction
{instruction}

### spreadsheet_path
{spreadsheet_path}

### spreadsheet_content
{spreadsheet_content}

### instruction_type
{instruction_type}

### answer_position
{answer_position}

### output_path
{output_path}

Note: DO NOT use excel formulas. Please calculate in Python and write the answer to the target cell or sheet directly. Please use the cell references to get the values, since your code will be applied to other spreadsheets."""

SECOND_ROUND_PROMPT = """Now, you need to generate a completed Python code to solve the question. The code should be placed in the markdown code field of the response, and the code should be executable in a Jupyter notebook environment. The code should save the modified spreadsheet file at the specified output_path.

Note: DO NOT use excel formulas. Please calculate in Python and write the answer to the target cell or sheet directly. Please use the cell references to get the values, since your code will be applied to other spreadsheets."""

class SpreadSheetSolver:

    def __init__(self, *args, **kwargs):
        
        self.url = kwargs.get('url', 'localhost:8000')
        self.code_exec_url = kwargs.get('code_exec_url', 'http://localhost:8081/execute')

        self.model_params = {
            'top_p': kwargs.get('top_p', 0.95),
            'temperature': kwargs.get('temperature', 0.6)
        }

        self.extractor = kwargs.get('extractor', 'base')

        self.suffix = kwargs.get('suffix', 'default')
        self.extractor = kwargs.get('extractor', 'base')
    
    def get_file_content(self, data):
        excel_file = pd.ExcelFile(os.path.join(data['real_dir'], data['input_file']))
        sheet_names = excel_file.sheet_names
        excel_data = {}

        for sheet_name in sheet_names:
            df = excel_file.parse(sheet_name)
            excel_data[sheet_name] = df.head(5).to_string()

        final_str = ""
        for sheet_name, sheet_str in excel_data.items():
            final_str += f"Sheet Name: {sheet_name}\n"
            final_str += sheet_str + "\n"
            final_str += "-" * 50 + "\n"
        
        spread_info = {}
        for sheet_name in sheet_names:
            target_path = os.path.join(data['real_dir'], data['input_file'].replace('.xlsx', f'_{sheet_name}_{self.extractor}.json'))

            if os.path.exists(target_path):
                with open(target_path, 'r') as f:
                    spread_info[sheet_name] = json.load(f)['structure']
        
        spread_info = "\n\n".join([f"### {k}\n{v}" for k, v in spread_info.items()])

        if spread_info:
            final_str += "\n\n### spreadsheet_information\n" + spread_info
        
        return final_str
    
    def get_solution(self, data, client, mount_dir):
        messages, solution, error = [], None, None

        try:
            input_path = f"/mnt/data/input/1_{data['id']}_input.xlsx"
            output_path = f"/mnt/data/output/1_{data['id']}_output.xlsx"

            file_content = self.get_file_content(data)

            prompt = FIRST_ROUND_PROMPT.format(
                instruction=data['instruction'],
                spreadsheet_path=input_path,
                spreadsheet_content=file_content,
                instruction_type=data['instruction_type'],
                answer_position=data['answer_position'],
                output_path=output_path
            )

            messages = [dict(role='user', content=prompt)]

            messages = tool_call_resp(
                self.url, 
                [python_tool], 
                messages, 
                turn_num=5,
                client=client,
                model_params=self.model_params,
                latex_url=self.url,
                mount_dir=mount_dir
            )
            
            messages.append({'role': 'user', 'content': SECOND_ROUND_PROMPT})
            
            resp = model_resp(
                self.url, 
                messages, 
                [python_tool],
                model_params=self.model_params
            )
            messages.append(resp['message'])
            
            solution = extract_code(messages[-1]['content'])
        except:
            error = traceback.format_exc()

        data.update(dict(messages=messages, error=error, solution=solution))

        return data

    def __call__(self, data):

        try:
            client = ClientJupyterKernel(self.code_exec_url, data['mount_dir'])

            for _ in range(3):
                data = self.get_solution(data, client, data['mount_dir'])

                if data['error'] is None:
                    break

            data = run_solution_one_data(data, client, self.suffix)
        except:
            traceback.print_exc()

        return data
