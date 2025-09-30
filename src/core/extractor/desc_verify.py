import traceback

from .base import register, StructureExtractor

from .no_structure import NO_STRUCTURE
from .json import JSON_STRUCTURE
from .yaml import YAML_STRUCTURE

from .desc import DESC_PROMPT, DESC_PROMPT_VISION, DESC_PROMPT_LATEX

from ..utils import tool_call_resp, model_resp, python_tool, convert_excel_to_image_tool, convert_excel_to_latex_tool, vision_question_answer_tool, latex_question_answer_tool


STRUCTURE_VERIFY = """You are a Spreadsheet Structure Verification Assistant. Your task is to verify whether a spreadsheet's structure matches the expected description provided. 

### Instructions:
1. Utilize the tool to get the infomation and determine if the structure is **correct and consistent**.  
2. If there are discrepancies (e.g., mismatched ranges, missing/extra rows or columns, incorrect headers, or formatting inconsistencies), describe them clearly and precisely.  
3. If the structure is valid, confirm that no issues were found.  

### Output Format:
```yaml
verification: true/false,
issues:
    - "Description of issue 1",
    - "Description of issue 2"
```
- verification is true: Structure is correct, "issues" should be an empty list.
- verification is false: One or more issues found, list them in "issues".

## Information to Verify:

- Spreadsheet Path: {spreadsheet_path}
- Sheet Name: {sheet_name}
- Used Range: {used_range}
- Spreadsheet Structure:
{spreadsheet_info}"""

@register('yaml_desc_verify')
class YamlDescVerifyStructureExtractor(StructureExtractor):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.prompt = YAML_STRUCTURE + '\n\n' + DESC_PROMPT
        self.second_prompt = """Based on the previous analysis, provide the final structural assessment, including the complete YAML configuration and any additional relevant details. Do not perform further examinations with tools; instead, directly deliver the final structure analysis."""

        self.tools = [vision_question_answer_tool, latex_question_answer_tool, python_tool]

    def get_or_fix_structure(self, messages, input_path, sheet_name, used_range, client, mount_dir):
        if messages is None:
            messages = [{'role': 'user', 'content': self.prompt % (
                input_path, sheet_name, used_range
            )}]

        messages = tool_call_resp(
            self.url, 
            self.tools, 
            messages,
            client=client, 
            vision_url=self.vision_url,
            latex_url=self.url,
            excel2image_url=self.excel2image_url,
            model_params=self.model_params,
            mount_dir=mount_dir
        )

        return messages
    
    def vision_verify(self, messages, docker_path, sheet_name, used_range, mount_dir):
        verify_prompt = STRUCTURE_VERIFY.format_map({
            'spreadsheet_path': docker_path,
            'sheet_name': sheet_name,
            'used_range': used_range,
            'spreadsheet_info': messages[-1]['content']
        })

        resp = tool_call_resp(
            self.vision_url, [convert_excel_to_image_tool],
            [{'role': 'user', 'content': verify_prompt}],
            model_params=self.model_params,
            mount_dir=mount_dir,
            excel2image_url=self.excel2image_url,
        )

        if 'verification: true' in resp[-1]['content']:
            result = True
        elif 'verification: false' in resp[-1]['content']:
            result = False
        else:
            result = None
            
        return result, resp
    
    def latex_verify(self, messages, docker_path, sheet_name, used_range, mount_dir):
        verify_prompt = STRUCTURE_VERIFY.format_map({
            'spreadsheet_path': docker_path,
            'sheet_name': sheet_name,
            'used_range': used_range,
            'spreadsheet_info': messages[-1]['content']
        })

        resp = tool_call_resp(
            self.url, [convert_excel_to_latex_tool],
            [{'role': 'user', 'content': verify_prompt}],
            model_params=self.model_params,
            mount_dir=mount_dir
        )

        if 'verification: true' in resp[-1]['content']:
            result = True
        elif 'verification: false' in resp[-1]['content']:
            result = False
        else:
            result = None
            
        return result, resp

    def get_structure_sheet(self, docker_path, sheet_name, used_range, client, mount_dir):
        messages, verify_messages, structure, error = None, [], None, "verification failed"

        try:
            for i in range(3):
                messages = self.get_or_fix_structure(
                    messages, docker_path, sheet_name, used_range, client, mount_dir
                )

                vision_verify_result, vision_verify_messages = self.vision_verify(messages, docker_path, sheet_name, used_range, mount_dir)
                latex_verify_result, latex_verify_messages = self.latex_verify(messages, docker_path, sheet_name, used_range, mount_dir)

                verify_messages.append(vision_verify_messages)
                verify_messages.append(latex_verify_messages)

                if vision_verify_result is False or latex_verify_result is False and i < 2:
                    verify_message = ""

                    if vision_verify_result is False:
                        verify_message += "Vision verification failed.\n\n" + vision_verify_messages[-1]['content']

                    if latex_verify_result is False:
                        verify_message += "Latex verification failed.\n\n" + latex_verify_messages[-1]['content']

                    messages.append(dict(role='user', content=verify_message))
                else:
                    error = None
                    break

            messages.append(dict(role='user', content=self.second_prompt))
            resp = model_resp(self.url, messages, [python_tool], model_params=self.model_params)
            
            if resp:
                messages.append(resp['message'])
                structure = messages[-1]['content']
        except:
            error = traceback.format_exc()
        
        return messages, structure, error, dict(verify_messages=verify_messages)

@register('yaml_desc_vision_verify')
class YamlDescVisionVerifyStructureExtractor(StructureExtractor):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.prompt = YAML_STRUCTURE + '\n\n' + DESC_PROMPT_VISION
        self.tools = [vision_question_answer_tool, python_tool]

@register('yaml_desc_latex_verify')
class YamlDescLatexVerifyStructureExtractor(StructureExtractor):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.prompt = YAML_STRUCTURE + '\n\n' + DESC_PROMPT_LATEX
        self.tools = [latex_question_answer_tool, python_tool]

@register('no_desc_verify')
class NoStructureVerifyStructureExtractor(YamlDescVerifyStructureExtractor):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prompt = NO_STRUCTURE + '\n\n' + DESC_PROMPT
        self.second_prompt = """Based on the previous analysis, provide the final structural assessment, including any additional relevant details. Do not perform further examinations with tools; instead, directly deliver the final structure analysis."""

@register('json_desc_verify')
class JSONVerifyStructureExtractor(YamlDescVerifyStructureExtractor):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prompt = JSON_STRUCTURE + '\n\n' + DESC_PROMPT
        self.second_prompt = """Based on the previous analysis, provide the final structural assessment, including the complete JSON configuration and any additional relevant details. Do not perform further examinations with tools; instead, directly deliver the final structure analysis."""