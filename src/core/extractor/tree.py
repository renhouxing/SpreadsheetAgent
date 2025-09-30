import traceback

from ..utils import tool_call_resp, python_tool

from .base import StructureExtractor, register

TREE_GENERATION = """You are tasked with performing detailed table analysis. Your task is to generate a hierarchical tree structure for the top-row and left-column headers based on a complex table.
(1). Task Description
[Reasoning Steps]
Your thought process is as follows:

- Understand the Table Structure: Provide a comprehensive description of the table, including the various levels of row and column headers and their corresponding meanings. Construct two distinct hierarchical trees: one for the row headers and one for the column headers. Each tree should accurately represent the levels and relationships of the headers.

- Traverse the Table: Analyze each row and column header to extract its content, indentation, and positions in the table. Identify merged cells and indentation, as they often indicate hierarchical relationships. Determine the parent-child relationships based on these visual cues and arrange the data under the correct parent node in both row and column header trees.

- Validate the Hierarchical Relationships: Iterate through both the row header tree and column header tree. Verify that the parent-child relationships are accurate and that the nodes are correctly placed within their respective hierarchies.

(2). Node Definition
You will be provided with a table in LaTeX format. The table may contain complex structures, such as merged or nested cells. Your task is to encode each node of table header as a tuple T(t1, t2, t3, t4)
The first element t1 indicates it represents row header (R) or column header (C), along with its corresponding level. 
The second element t2 and third element t3 represent its start and end positions, while the fourth element t4 contains the value from the table. For example, a tuple (R0, 1, 2, City) indicates that it is a row header (R) at level 0, spanning from row 1 to row 2, with the value City.
Please Convert the table headers to list L=[T1, T2, ...]

(3). Tree Generate
1. Divide the tuples list L into groups based on their levels, such that all tuples with the same level are grouped together. Add a special ROOT node for rows and columns, each with a level of "-1".
2. For each tuple A in L. If the start and end positions of A are equal, mark A as a leaf node.
3. Otherwise, compare its T2 and T3 values with every closest higher-level and same flag tuple B. If tuple A is within the range of tuple B, then B is the parent-header of A.
4. Repeat steps 2 and 3 iteratively until all tuples in L are linked to their respective parent nodes (Tuples without parent node are linked to the ROOT node), forming a hierarchical Table-Header Tree H.

(4) Next, we will provide a table for you to analyze the hierarchical structure for the table and please organize the table header tuples as a tree, which can help you better understand the table structure.
Your should clearly and comprehensively understanding the content of the table, including the structure of the table, the meaning and formatting of each row and column header (Note: There is usually summative cell in the table, such as all, combine, total, sum, average, mean, etc. Please pay careful attention to the flag information in the row header and column header, this information can help you to skip many operations.)

Please check the constructed tree structure carefully and make sure that you have not missed any information in the contents of the table.
Let's get started!

### spreadsheet_path
{spreadsheet_path}

### sheet_name
{sheet_name}

### used_range
{used_range}"""

@register('tree')
class TreeStructureExtractor(StructureExtractor):

    def get_structure_sheet(self, docker_path, sheet_name, used_range, client, mount_dir):
        messages, structure, error = [], None, None

        try:
            first_round_prompt = TREE_GENERATION.format(
                spreadsheet_path=docker_path,
                sheet_name=sheet_name,
                used_range=used_range
            )

            messages = [{'role': 'user', 'content': first_round_prompt}]
            messages = tool_call_resp(
                self.url, 
                [python_tool],
                messages,
                client=client,
                model_params=self.model_params
            )
            structure = messages[-1]['content']
        except:
            error = traceback.format_exc()
        
        return messages, structure, error, {}
