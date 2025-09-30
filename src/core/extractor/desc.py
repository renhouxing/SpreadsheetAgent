import traceback

from ..utils import tool_call_resp, python_tool, vision_question_answer_tool, latex_question_answer_tool

from .base import StructureExtractor, register

from .yaml import YAML_STRUCTURE
from .json import JSON_STRUCTURE
from .no_structure import NO_STRUCTURE

DESC_PROMPT = """During the analysis, you should primarily use the Python tool to parse and analyze table or structured data.

Only when you encounter complex structures (such as merged cells, multi-level headers, or formatting details that cannot be clearly inferred from cell values alone), you MUST call both the visual tool and the latex tool on a small range for double verification.

Avoid delegating the entire task to the tools—ensure that the core analysis and structure recognition are mainly handled by the Python tool."""

DESC_PROMPT_VISION = """During the analysis, you should primarily use the Python tool to parse and analyze table or structured data.

Only when you encounter complex structures (such as merged cells, multi-level headers, or formatting details that cannot be clearly inferred from cell values alone), you MUST call the visual tool on a small range for double verification.

Avoid delegating the entire task to the tool—ensure that the core analysis and structure recognition are mainly handled by the Python tool."""

DESC_PROMPT_LATEX = """During the analysis, you should primarily use the Python tool to parse and analyze table or structured data.

Only when you encounter complex structures (such as merged cells, multi-level headers, or formatting details that cannot be clearly inferred from cell values alone), you MUST call the latex tool on a small range for double verification.

Avoid delegating the entire task to the tool—ensure that the core analysis and structure recognition are mainly handled by the Python tool."""

@register('yaml_desc')
class YamlDescStructureExtractor(StructureExtractor):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.prompt = YAML_STRUCTURE + '\n\n' + DESC_PROMPT
        self.tools = [vision_question_answer_tool, latex_question_answer_tool, python_tool]

    def get_structure_sheet(self, docker_path, sheet_name, used_range, client, mount_dir):
        messages, structure, error = [], None, None

        try:
            messages = [{'role': 'user', 'content': self.prompt % (
                docker_path, sheet_name, used_range
            )}]

            messages = tool_call_resp(
                self.url, 
                self.tools, 
                messages,
                client=client,
                latex_url=self.url,
                vision_url=self.vision_url,
                excel2image_url=self.excel2image_url,
                model_params=self.model_params,
                mount_dir=mount_dir
            )
            
            structure = messages[-1]['content']
        except:
            error = traceback.format_exc()
        
        return messages, structure, error, {}

@register('yaml_desc_vision')
class YamlDescVisionStructureExtractor(YamlDescStructureExtractor):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.prompt = YAML_STRUCTURE + '\n\n' + DESC_PROMPT_VISION
        self.tools = [vision_question_answer_tool, python_tool]

@register('yaml_desc_latex')
class YamlDescLatexStructureExtractor(YamlDescStructureExtractor):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.prompt = YAML_STRUCTURE + '\n\n' + DESC_PROMPT_LATEX
        self.tools = [latex_question_answer_tool, python_tool]

@register('no_desc')
class NoDescStructureExtractor(YamlDescStructureExtractor):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.prompt = NO_STRUCTURE + '\n\n' + DESC_PROMPT

@register('json_desc')
class JsonDescStructureExtractor(YamlDescStructureExtractor):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.prompt = JSON_STRUCTURE + '\n\n' + DESC_PROMPT