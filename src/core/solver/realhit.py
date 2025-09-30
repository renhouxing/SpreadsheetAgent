import os
import sys
import json
import traceback

import numpy as np
import pandas as pd

import matplotlib.pyplot as plt

from ..utils import model_resp, tool_call_resp, python_tool
from ..client import ClientJupyterKernel

from .realhit_prompts import *

import re
import ast
from .metrics.qa_metrics import QAMetric

def get_answer_format(query):
    answer_format = ""
    if query['SubQType'] == 'Exploratory Analysis':
        answer_format = "CorrelationRelation, CorrelationCoefficient"
    elif query['QuestionType'] == 'Visualization':
        answer_format = "import pandas as pd\nimport matplotlib.pyplot as plt\nyour code here\nplt.show()"
    else:
        answer_format = "AnswerName1, AnswerName2, ..."
    return answer_format

def get_final_answer(response):

    if "[Final Answer]:" in response:
        final_answer = response.split("[Final Answer]:")[-1].strip()
        return final_answer
    elif "Final Answer:" in response:
        final_answer = response.split("Final Answer:")[-1].strip()
        return final_answer
    return str(response).strip()

def surround_pycode_with_main(pycode):
    start_line = '''
if __name__ == '__main__':
'''
    pycode_lines = pycode.strip().split('\n')
    for line in pycode_lines:
        start_line += f'    {line}\n'
    return start_line

def visualization_code_format(visualization_answer):
    
    pattern1 = r"import pandas as pd.*?plt\.show\(\)"
    pattern2 = r"import matplotlib.pyplot as plt.*?plt\.show\(\)"
    try:
        matches1 = re.findall(pattern1, visualization_answer, flags=re.S)
        if matches1:
            return matches1[-1]
        else:
            matches2 = re.findall(pattern2, visualization_answer, flags=re.S)
            if matches2:
                return matches2[-1]
            else:
                print(f"invalid visualization_answer: {visualization_answer}\n")
                return ''
    except Exception as e:
        print(f"visualization_code_format failed which is: {visualization_answer}")

def build_eval_code(answer_code, chart_type):
    extract_code = visualization_code_format(answer_code)
    python_code_lines = extract_code.strip().split('\n')

    eval_code = '''
if chart_type == 'LineChart': 
    y_predictions = get_line_y_predictions(plt)
if chart_type == 'BarChart':
    y_predictions = get_bar_y_predictions(plt)
if chart_type == 'ScatterChart':
    y_predictions = get_scatter_y_predictions(plt)
if chart_type == 'PieChart':
    y_predictions = get_pie_y_predictions(plt)

print(y_predictions)
'''
    python_code = ""
    for line in python_code_lines:
        python_code += f"{line.strip(' ')}\n"
    chart_eval_code = f'    from utils.chart_metric_util import *\n{python_code}\nchart_type="{chart_type}"\n{eval_code}'
    return python_code, chart_eval_code

def exec_and_get_y_reference(answer_code, chart_type):
    ecr_1 = False
    python_code, eval_code = build_eval_code(answer_code, chart_type)
    # print("Code:", python_code)
    if python_code == "":
        return "", False
    try:
        python_code = surround_pycode_with_main(python_code)
        exec(python_code)
        plt.close("all")
        ecr_1 = True
    except Exception as e:
        print("Python Error: ", e, python_code)
        ecr_1 = False
        return "", False
    if ecr_1:
        pass
    try: 
        from io import StringIO
        output = StringIO()
        stdout = sys.stdout
        try:
            sys.stdout = output
            chart_eval_code = surround_pycode_with_main(eval_code)
            exec(chart_eval_code)
        except Exception as e:
            print("Eval Error: ", e, chart_eval_code)
            return "", True
        finally:
            sys.stdout = stdout
        output_value = output.getvalue()
        # print("OUTPUT VALUE: ",output_value)
    except Exception as e:
        print("Eval Error: ",e)
        output_value = ''

    if output_value != '':
        parsed_prediction = output_value.strip()
    else:
        parsed_prediction = ''
    plt.close('all')
    return parsed_prediction, ecr_1

def compare(list1, list2):
    # sort the list
    list1.sort()
    list2.sort()
    if len(list1) != len(list2):
        return False
    for i in range(len(list1)):
        if np.isnan(list1[i]):
            if not np.isnan(list2[i]):
                return False
        elif list1[i] != list2[i]:
            return False
    return True

def std_digit(list_nums):
    new_list = []
    for i in range(len(list_nums)):
        new_list.append(round(list_nums[i], 2))
    return new_list

def compute_general_chart_metric(references, predictions):
    processed_references = []
    processed_predictions = []
    for reference in references:
        if isinstance(reference, list):
            processed_references.extend(reference)
        else:
            processed_references.append(reference)

    for prediction in predictions:
        if isinstance(prediction, list):
            processed_predictions.extend(prediction)
        else:
            processed_predictions.append(prediction)
    processed_references = std_digit(processed_references)
    processed_predictions = std_digit(processed_predictions)
    return compare(processed_references, processed_predictions)


def compute_pie_chart_metric(references, predictions):
    processed_references = []
    processed_predictions = []
    for reference in references:
        if isinstance(reference, list):
            processed_references.extend(reference)
        else:
            processed_references.append(reference)
    references = processed_references
    processed_references = []
    total = 0
    for reference in references:
        total += reference
    for reference in references:
        processed_references.append(round(reference / total, 2))

    for prediction in predictions:
        if isinstance(prediction, list):
            processed_predictions.extend(prediction)
        else:
            processed_predictions.append(prediction)
    processed_references = std_digit(processed_references)
    processed_predictions = std_digit(processed_predictions)
    return compare(processed_references, processed_predictions)

class RealHiTSolver:

    def __init__(self, *args, **kwargs):
        
        self.url = kwargs.get('url', 'localhost:8000')
        self.code_exec_url = kwargs.get('code_exec_url', 'http://localhost:8081/execute')

        self.model_params = {
            'top_p': kwargs.get('top_p', 1.0),
            'temperature': kwargs.get('temperature', 0)
        }

        self.suffix = kwargs.get('suffix', 'default')
        self.extractor = kwargs.get('extractor', 'base')

        self.use_python_tool = kwargs.get('use_python_tool', False)
    
    def get_file_content(self, path):
        excel_file = pd.ExcelFile(path)
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
            target_path = path.replace('.xlsx', f'_{sheet_name}_{self.extractor}.json')

            if os.path.exists(target_path):
                with open(target_path, 'r') as f:
                    spread_info[sheet_name] = json.load(f)['structure']
        
        spread_info = "\n\n".join([f"### {k}\n{v}" for k, v in spread_info.items()])

        if spread_info:
            final_str += "\n\n### spreadsheet_information\n" + spread_info
        
        return final_str
    
    def get_solution(self, data, client):
        messages, solution, error = [], '', None

        try:
            if data['QuestionType'] == 'Data Analysis': 
                second_prompt = Answer_Prompt[data['SubQType']]
            else:
                second_prompt = Answer_Prompt[data['QuestionType']]

            sheet_name = pd.ExcelFile(os.path.join(data['real_dir'], f"{data['FileName']}.xlsx")).sheet_names[0]
            target_structure_path = os.path.join(data['real_dir'], f"{data['FileName']}_{sheet_name}_{self.suffix}.json")
            
            structure_info = ''
            if os.path.exists(target_structure_path):
                with open(target_structure_path, 'r') as f:
                    structure_info = json.load(f)['structure']
                    structure_info = '\n\n# Excel Structure\n' + structure_info

            if self.use_python_tool:
                spreadsheet_content = self.get_file_content(f"{data['real_dir']}/{data['FileName']}.xlsx")

                messages = [dict(
                    role='user', 
                    content=User_Prompt_Python.format(
                        instruction=data['Question'],
                        spreadsheet_path=f"/mnt/data/input/{data['FileName']}.xlsx",
                        spreadsheet_content=spreadsheet_content,
                    )
                )]

                messages = tool_call_resp(
                    self.url, 
                    [python_tool], 
                    messages, 
                    client=client,
                    model_params=self.model_params
                )

                messages.append({'role': 'user', 'content': second_prompt})

                resp = model_resp(
                    self.url, 
                    messages, 
                    [python_tool],
                    model_params=self.model_params
                )
                messages.append(resp['message'])
            else:
                with open(f"{data['real_dir']}_latex/{data['FileName']}.txt", 'r') as f:
                    table = f.read()
                    
                spreadsheet_content = table + "\n\n" + self.get_file_content(f"{data['real_dir']}/{data['FileName']}.xlsx")

                messages = [dict(
                    role='user', 
                    content=User_Prompt_Normal.format(
                        instruction=data['Question'],
                        spreadsheet_content=spreadsheet_content,
                    )
                )]

                resp = model_resp(
                    self.url, 
                    messages, 
                    model_params=self.model_params
                )

                messages.append({'role': 'user', 'content': resp['message']['content']})
                messages.append({'role': 'user', 'content': second_prompt})

                resp = model_resp(
                    self.url, 
                    messages, 
                    model_params=self.model_params
                )
                messages.append(resp['message'])


            solution = messages[-1]['content']
        except:
            error = traceback.format_exc()

        data.update(dict(messages=messages, error=error, solution=solution))

        return data

    def __call__(self, data):
        metric_scores = {}

        try:
            client = ClientJupyterKernel(self.code_exec_url, data['mount_dir'])
            for _ in range(3):
                data = self.get_solution(data, client)
                if data['error'] is None:
                    break

            reference = data['ProcessedAnswer']
            response = ""
            if data['QuestionType'] == 'Visualization':
                chart_type = data['SubQType'].split()[0]
                response = get_final_answer(data['solution']).replace('/mnt/data/input', data['real_dir'])
                prediction, ecr_1 = exec_and_get_y_reference(response, chart_type)
                metric_scores['ECR'] = ecr_1
                if prediction != '':
                    try:
                        prediction = ast.literal_eval(prediction)
                        reference = ast.literal_eval(reference)
                        if chart_type == 'PieChart': 
                            metric_scores['Pass'] = compute_pie_chart_metric(reference, prediction)
                        else: 
                            metric_scores['Pass'] = compute_general_chart_metric(reference, prediction)
                    except Exception as e:
                        metric_scores['Pass'] = 'False'
                else:
                    metric_scores['Pass'] = None
            elif data['QuestionType'] == 'Structure Comprehending':
                for _ in range(3):
                    data = self.get_solution(data, client)
                    if data['error'] is None:
                        break
                reference = get_final_answer(data['solution'])
                data["FileName"] = data["FileName"] + "_swap"
                for _ in range(3):
                    data = self.get_solution(data, client)
                    if data['error'] is None:
                        break
                response = get_final_answer(data['solution'])
                metric_scores = QAMetric().compute([reference], [response])
            else:
                for _ in range(3):
                    data = self.get_solution(data, client)
                    if data['error'] is None:
                        break
                response = get_final_answer(data['solution'])
                metric_scores = QAMetric().compute([reference], [response])
        except:
            pass
            # traceback.print_exc()
        
        data['eval'] = {
            'Model_Answer': response,
            "Reference_Answer": reference,
            'F1': metric_scores.get('F1', None),
            'EM': metric_scores.get('EM', None),
            'ROUGE-L': metric_scores.get('ROUGE-L', None),
            'SacreBLEU': metric_scores.get('SacreBLEU', None),
            'ECR': metric_scores.get('ECR', None),
            'Pass': metric_scores.get('Pass', None)
        }

        return data
