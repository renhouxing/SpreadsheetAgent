import traceback

from ..utils import tool_call_resp, python_tool

from .base import StructureExtractor, register

NO_STRUCTURE = """You are a spreadsheet expert who can analyze spreadsheets using Python. Your task is to detect tables in a spreadsheet and summaize high-level infomation for them, including metadata, hierarchical structures, data properties, and other essential infomation.  

(1) Detect All Tables
  Identify all rectangular areas in the spreadsheet that can be considered tables. A table is defined as a block with identifiable headers and corresponding data. Clarify how to handle:
  - Empty rows/columns (skip or stop).
  - Multiple adjacent tables (detect separately).
  - Merged cells (treat as higher-level headers). 

(2) Analyze and Output Table Structure

#### a. Metadata
- Sheet Name: The sheet containing the table.  
- Table Name: If defined (e.g., Table1 in Excel).  
- Table Range: The full rectangular range of the table (e.g., A1:D20).  
- Data Range: The rectangular range containing only data (excluding headers).  
- Notes / Footnotes: Optional annotations or data source lines below the table. 

#### b. Header Structure
- Determine Header Format
  First, classify the table structure into one of the following:  
  - Column-only header (most common: header row(s) at the top)  
  - Row-only header (rare: header column(s) on the left)  
  - Both row & column headers (matrix-style tables)  

- Detect all header cell:  
  Each header cell have three attributes: start position, end position, and value.  
  - Start Position: The coordinate of the top-left cell of the header (e.g., A1).  
  - End Position: The coordinate of the bottom-right cell of the header (e.g., B2).  
  - Value: The text content of the header cell.

- Group header cells with the same level:
  Headers can be nested, indicating hierarchical relationships. Group headers based on their indentation levels. For example, if "Country" spans two columns and "State" and "City" are under it, they should be grouped accordingly. 

- Construct hierarchical structures:
  Build the hierarchical structure for both row and column headers.  Each node in the hierarchy should include:
  - Start Index: The starting cell coordinate of the header.
  - End Index: The ending cell coordinate of the header.
  - Value: The text content of the header.
  - Children: A list of child nodes representing sub-headers.

#### c. Data Properties
For each column (or row header if applicable), detect:  
- Data Type (string, number, date, boolean, mixed)  
- Unit (if explicit, e.g., km, dollar)
- Format (e.g., bold, italic, background color, currency) 

### spreadsheet_path
%s

### sheet_name
%s

### used_range
%s"""

@register('no')
class NoStructureExtractor(StructureExtractor):

    def get_structure_sheet(self, docker_path, sheet_name, used_range, client, mount_dir):
        messages, structure, error = [], None, None

        try:
            messages = [{'role': 'user', 'content': NO_STRUCTURE % (
                docker_path, sheet_name, used_range
            )}]

            messages = tool_call_resp(
                self.url, 
                [python_tool],
                messages,
                client=client,
                model_params=self.model_params
            )
            
            structure = messages[-1]['content']
        except:
            traceback.print_exc()
            error = traceback.format_exc()
        
        return messages, structure, error
