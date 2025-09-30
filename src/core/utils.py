import os
import json
import requests
import traceback

def load_jsonl(path):
    if path.endswith('.json'):
        with open(path, 'r') as f:
            return json.load(f)
    elif path.endswith('.jsonl'):
        with open(path, 'r') as f:
            return [json.loads(line) for line in f.readlines()]
    else:
        raise ValueError(f"Unsupported file format: {path}")

def save_jsonl(data, path):
    if path.endswith('.json'):
        with open(path, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    elif path.endswith('.jsonl'):
        with open(path, 'w') as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
    else:
        raise ValueError(f"Unsupported path: {path}")

python_tool = {
    "type": "function",
    "function": {
        "name": "execute_python",
        "description": "When you send a message containing Python code to python, it will be executed in a stateful Jupyter notebook environment. python will respond with the output of the execution or time out after 60.0 seconds. The drive at '/mnt/data' can be used to save and persist user files. Internet access for this session is disabled.",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "The Python code to execute",
                }
            },
            "required": ["code"]
        },
    }
}

def execute_python(arguments, **kwargs):
    try:
        client = kwargs.get('client', None)
        if not client:
            raise ValueError("Client is required to execute Python code.")
        if isinstance(arguments, str) and arguments.startswith('{'):
            arguments = json.loads(arguments)
            code = arguments.pop('code', None)
        else:
            code = arguments
        exec_result = client.execute(code)
    except Exception as e:
        exec_result = traceback.format_exc()
    return dict(role='tool', content=exec_result)

convert_excel_to_image_tool = {
    "type": "function",
    "function": {
        "name": "convert_excel_to_image",
        "description": "Extracts an image from a specified spreadsheet file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The file path to the Excel file."
                },
                "sheet_name": {
                    "type": "string",
                    "description": "The name of the sheet from which to extract the image."
                },
                "range": {
                    "type": "string",
                    "description": "The cell range to search for the image (e.g., 'A1:D20'). Use to limit extraction to a specific area. Images smaller than 8192×16384 pixels are supported, so keep the range within reasonable bounds."
                }
            },
            "required": ["path", "sheet_name", "range"]
        }
    }
}

def get_excel_image(path, sheet_name, _range=None):
    try:
        resp = requests.post(
            "http://localhost:8007/excel2img", 
            files=dict(file=open(path, "rb")), 
            data=dict(page=sheet_name, _range=_range)
        )
        resp = resp.json()
        return resp
    except Exception as e:
        return dict(error='Processing error')

# Get the repository directory
repo_dir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def convert_excel_to_image(arguments, **kwargs):
    mount_dir = kwargs.get('mount_dir', None)
    if not mount_dir:
        return dict(role='tool', content="mount_dir is required to extract image.")

    try:
        arguments = json.loads(arguments)
        path = arguments['path'].replace('/mnt/data/spreadsheet', os.path.join(repo_dir, 'data/spreadsheet'))

        for k, v in mount_dir.items():
            path = path.replace(v, k)

        resp = get_excel_image(
            path=path,
            sheet_name=arguments['sheet_name'],
            _range=arguments.get('range', None),
        )
        
        if 'error' in resp:
            return dict(role='tool', content=f"Error extracting image: {resp['error']}")
        else:
            return {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{resp['image_base64']}"
                        },
                    }
                ],
            }
    except:
        return dict(role='tool', content=traceback.format_exc())

convert_excel_to_latex_tool = {
    "type": "function",
    "function": {
        "name": "convert_excel_to_latex",
        "description": "Converts an Excel file to a LaTeX file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The file path to the Excel file."
                },
                "sheet_name": {
                    "type": "string",
                    "description": "The name of the sheet from which to extract the image."
                },
                "range": {
                    "type": "string",
                    "description": "The cell range to convert to LaTeX. Use to limit conversion to a specific area."
                }
            },
            "required": ["path", "sheet_name", "range"]
        }
    }
}

from .excel2tex import convert_excel_to_latex as convert_excel_to_latex_func

def convert_excel_to_latex(arguments, **kwargs):
    mount_dir = kwargs.get('mount_dir', None)
    if not mount_dir:
        return dict(role='tool', content="mount_dir is required to extract image.")

    try:
        arguments = json.loads(arguments)
        path = arguments['path'].replace('/mnt/data/spreadsheet', os.path.join(repo_dir, 'data/spreadsheet'))

        for k, v in mount_dir.items():
            path = path.replace(v, k)

        resp = convert_excel_to_latex_func(
            path=path,
            sheet_name=arguments['sheet_name'],
            _range=arguments['range'],
        )
        
        if 'error' in resp:
            return dict(role='tool', content=f"Error converting Excel to LaTeX: {resp['error']}")
        else:
            return {
                "role": "tool",
                "content": resp
            }
    except:
        return dict(role='tool', content=traceback.format_exc())

vision_question_answer_tool = {
    "type": "function",
    "function": {
        "name": "vision_question_answer",
        "description": "You can analyze a selected range of cells in a spreadsheet using vision capabilities. When asking, focus on small, well-defined questions and describe all relevant details — don't just hand over your entire task to the tool.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The file path to the spreadsheet containing the image."
                },
                "sheet_name": {
                    "type": "string",
                    "description": "The name of the sheet from which to extract the image."
                },
                "range": {
                    "type": "string",
                    "description": "Optional. The cell range to search for the image (e.g., 'A1:D20'). Use to limit extraction to a specific area. Images smaller than 8192×16384 pixels are supported, so keep the range within reasonable bounds."
                },
                "question": {
                    "type": "string",
                    "description": "The question to answer about the specified range of cells."
                }
            },
            "required": ["path", "sheet_name", "range", "question"]
        }
    }
}

def vision_question_answer(arguments, **kwargs):

    vision_url = kwargs.get('vision_url', None)
    if not vision_url:
        return dict(role='tool', content="Vision URL is required to answer the question.")
    
    model_params = kwargs.get('model_params', None)
    if not model_params:
        return dict(role='tool', content="Model parameters are required to answer the question.")
    
    mount_dir = kwargs.get('mount_dir', None)
    if not mount_dir:
        return dict(role='tool', content="mount_dir is required to extract image.")

    try:
        arguments = json.loads(arguments)

        path = arguments['path']
        for k, v in mount_dir.items():
            path = path.replace(v, k)

        resp = get_excel_image(
            path=path,
            sheet_name=arguments['sheet_name'],
            _range=arguments.get('range', None),
        )
        
        messages = [{
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{resp['image_base64']}"
                    },
                },
                {
                    "type": "text",
                    "text": arguments['question']
                }
            ]
        }]
        resp = model_resp(vision_url, messages, model_params=model_params)
        
        content = resp['message']['content']
        return dict(role='tool', content=content)
    except:
        return dict(role='tool', content=traceback.format_exc())

latex_question_answer_tool = {
    "type": "function",
    "function": {
        "name": "latex_question_answer",
        "description": "You can analyze a selected range of cells in a spreadsheet using latex capabilities. When asking, focus on small, well-defined questions and describe all relevant details — don't just hand over your entire task to the tool.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The file path to the Excel file."
                },
                "sheet_name": {
                    "type": "string",
                    "description": "The name of the sheet from which to extract the latex."
                },
                "range": {
                    "type": "string",
                    "description": "Optional. The cell range to search for the latex (e.g., 'A1:D20'). Use to limit extraction to a specific area."
                },
                "question": {
                    "type": "string",
                    "description": "The question to answer about the specified range of cells."
                }
            },
            "required": ["path", "sheet_name", "range", "question"]
        }
    }
}

def latex_question_answer(arguments, **kwargs):

    latex_url = kwargs.get('latex_url', None)
    if not latex_url:
        return dict(role='tool', content="Latex URL is required to answer the question.")
    
    model_params = kwargs.get('model_params', None)
    if not model_params:
        return dict(role='tool', content="Model parameters are required to answer the question.")
    
    mount_dir = kwargs.get('mount_dir', None)
    if not mount_dir:
        return dict(role='tool', content="mount_dir is required to extract image.")

    try:
        if not isinstance(arguments, dict):
            arguments = json.loads(arguments)

        path = arguments['path']
        for k, v in mount_dir.items():
            path = path.replace(v, k)

        resp = convert_excel_to_latex_func(
            path=path,
            sheet_name=arguments['sheet_name'],
            _range=arguments.get('range', None),
        )
        
        messages = [{
            "role": "user",
            "content": resp + '\n\n' + arguments['question']
        }]
        resp = model_resp(latex_url, messages, model_params=model_params)
        
        content = resp['message']['content']
        return dict(role='tool', content=content)
    except:
        return dict(role='tool', content=traceback.format_exc())

def model_resp(
    url, 
    messages, 
    tools=None,
    model_params=None
):  
    parameters = dict(
        messages=messages,
        model='model',
        max_tokens=4096,
        temperature=0.95,
        top_p=0.6,
        skip_special_tokens=False,
        spaces_between_special_tokens=False,
        chat_template_kwargs={"enable_thinking": False}
    )

    if model_params:
        parameters.update(model_params)

    if tools:
        parameters['tools'] = tools
        parameters['tool_choice'] = 'auto'

    for _ in range(3):
        try:
            resp = requests.post(
                url=f"http://{url}/v1/chat/completions", 
                json=parameters, verify=False
            ).json()

            if 'choices' in resp:
                resp = resp['choices'][0]
                return resp
        except:
            import traceback
            traceback.print_exc()
            pass
        
    return None

def tool_call_resp(
    url, 
    tools, 
    messages, 
    turn_num=20, 
    break_condition=lambda x: False,
    model_params=None,
    **kwargs
):
    for _ in range(turn_num):
        resp = model_resp(url, messages, tools, model_params=model_params)

        if not resp:
            break
            
        messages.append(resp['message'])

        if resp['finish_reason'] != 'tool_calls':
            break
        
        for tool_call in resp['message']['tool_calls']:
            func = globals()[tool_call['function']['name']]

            if func:
                message = func(
                    tool_call['function']['arguments'], 
                    model_params=model_params, 
                    **kwargs
                )
                message['tool_call_id'] = tool_call['id']
            else:
                message = dict(
                    role='tool', 
                    tool_call_id=tool_call['id'], 
                    content=f"Unknown tool: {tool_call['function']['name']}"
                )
            messages.append(message)

        if break_condition(resp):
            break

    return messages