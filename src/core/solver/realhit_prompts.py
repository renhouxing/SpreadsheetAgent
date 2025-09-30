Fact_Checking = """
# Output Control
1、The final answer should be one-line and strictly follow the format: "[Final Answer]: AnswerName1, AnswerName2...". 
2、Ensure the "AnswerName" is a number or entity name, as short as possible, without any explanation. Give the final answer to the question directly without any explanation. If the question is judgmental, please answer 'Yes' or 'No'.
**Format:** [Final Answer]: AnswerName1, AnswerName2...
"""

Numerical_Reasoning = """
# Output Control
1、The final answer should be one-line and strictly follow the format: "[Final Answer]: AnswerName1, AnswerName2...". 
2、Ensure the "AnswerName" is a number or entity name, as short as possible, without any explanation. Give the final answer to the question directly without any explanation. Note: If the answer involves decimals, always keep it to two decimals.
**Format:** [Final Answer]: AnswerName1, AnswerName2...
"""

Rudimentary_Analysis = """
# Output Control
1、You only need to output the final answer without any interpretation. 
2、The final answer should be one-line and strictly follow the format: "[Final Answer]: AnswerName1, AnswerName2...". Note: If the answer involves decimals, always keep it to two decimals.
3、The "AnswerName" should represent the primary result of the rudimentary analysis, such as a number or an entity name, expressed as concisely as possible. Provide the final answer directly without additional explanation or extra output.
**Format:** [Final Answer]: AnswerName1, AnswerName2...
"""

Summary_Analysis = """
# Output Control
1、You only need to output the final answer without any interpretation. 
2、The final answer should be one-line and strictly follow the format: "[Final Answer]: TableSummary". 
3、The "TableSummary" should provide a concise summary of the table, including a brief description of its content, the main columns, and any basic insights derived. Provide the final answer directly without additional explanation or extra output.
**Format:** [Final Answer]: TableSummary.
"""

Predictive_Analysis = """
# Output Control
1、You only need to output the final answer without any interpretation. 
2、The final answer should be one-line and strictly follow the format: "[Final Answer]: AnswerName1, AnswerName2...". Note: If the answer involves decimals, always keep it to two decimals.
3、The "AnswerName" should summarize the primary result of the analysis in a concise manner, such as a number, an entity name, or a trend description (e.g., No clear trend, Increasing trend, Decreasing trend).  Provide the final answer directly without additional explanation or extra output. Note: If the final answer has multiple decimals, retain two decimals. 
**Format:** [Final Answer]: AnswerName1, AnswerName2...
"""

Exploratory_Analysis = """
# Output Control
1、You only need to output the final answer without any interpretation. 
2、The final answer should be one-line and strictly follow the format: "[Final Answer]: CorrelationRelation, CorrelationCoefficient." Note: If the answer involves decimals, always keep it to two decimals.
3、Ensure that: the correlation coefficient should be a float number with two decimal places; the correlation relation can only be "No correlation" with the correlation coefficient between -0.3 to +0.3, "Weak positive correlation" with the correlation coefficient between +0.3 to +0.7, "Weak negative correlation" with the correlation coefficient between -0.3 to -0.7, "Strong positive correlation" with the correlation coefficient between +0.7 to +1, or "Strong negative correlation" with the correlation coefficient between -0.7 to -1. If the question is about impact analysis, the "AnswerName" should be a entity name or a impact description(No clear impact, Negtive impact or Positive impact), as short as possible, without any explanation. If the question is about causal analysis, the "AnswerName" should be a brief explanation of the causal analysis results as concise as possible. Note: If the final answer has multiple decimals, retain two decimals. 
**Format:** [Final Answer]: CorrelationRelation, CorrelationCoefficient
"""

Anomaly_Analysis = """
# Output Control
1、You only need to output the final answer without any interpretation. 
2、The final answer should be one-line and strictly follow the format: "[Final Answer]: Conclusion."
3、The "Conclusion" should provide a concise conclusion of the table anomaly. Provide the final answer directly without additional explanation or extra output.
**Format:** [Final Answer]: Conclusion
"""

Visulization = """
# Output Control
1、The final answer should follow the format below and ensure the first three code lines is exactly the same with the following code block: [Final Answer]: import pandas as pd \n import matplotlib.pyplot as plt \n ... plt.show(). 
2、You only need to output the final code without any interpretation, make sure that your code can be run directly without any syntax errors.
3、Please make sure the table is named “table.xlsx”, and the pandas and matplotlib libraries have been successfully introduced.
4、Ensure that the X-axis used for drawing in the code is arranged in ascending alphabetical or numerical order. Ensure the last line in python code can only be "plt.show()", no other from. Give the final answer to the question directly without any explanation.
**Format:** [Final Answer]: import pandas as pd \n import matplotlib.pyplot as plt \n ... plt.show()
"""

Structure_Comprehending = """
# Output Control
1、The final answer should be one-line and strictly follow the format: "[Final Answer]: AnswerName1, AnswerName2...". 
2、Ensure the "AnswerName" is a number or entity name, as short as possible, without any explanation. Give the final answer to the question directly without any explanation. If the question is judgmental, please answer 'Yes' or 'No'.
**Format:** [Final Answer]: AnswerName1, AnswerName2...
"""

User_Prompt = """ 
You are a spreadsheet expert.

# Table
{Table}
# Question
{Question}

Please reasoning step by step. 
"""

User_Prompt_Normal = """You are a spreadsheet expert.

You need to solve the given spreadsheet manipulation question, which contains six types of information:
- instruction: The question about spreadsheet manipulation.
- spreadsheet_content: The first few rows of the content of speadsheet file.
- spreadsheet_information: The hierarchical structure of the spreadsheet. It contains information about the row and column headers, including their levels, start and end positions, and values.

Below is the spreadsheet manipulation question you need to solve:
### instruction
{instruction}

### spreadsheet_content
{spreadsheet_content}"""

User_Prompt_Python = """You are a spreadsheet expert who can manipulate spreadsheets through Python code.

You need to solve the given spreadsheet manipulation question, which contains six types of information:
- instruction: The question about spreadsheet manipulation.
- spreadsheet_path: The path of the spreadsheet file you need to manipulate.
- spreadsheet_content: The first few rows of the content of speadsheet file.
- spreadsheet_information: The hierarchical structure of the spreadsheet. It contains information about the row and column headers, including their levels, start and end positions, and values.

Below is the spreadsheet manipulation question you need to solve:
### instruction
{instruction}

### spreadsheet_path
{spreadsheet_path}

### spreadsheet_content
{spreadsheet_content}"""

Answer_Prompt = {
    "Fact Checking": Fact_Checking,
    "Numerical Reasoning": Numerical_Reasoning,
    "Structure Comprehending": Structure_Comprehending,
    "Rudimentary Analysis": Rudimentary_Analysis,
    "Summary Analysis": Summary_Analysis,
    "Predictive Analysis": Predictive_Analysis,
    "Exploratory Analysis": Exploratory_Analysis,
    "Anomaly Analysis": Anomaly_Analysis,
    "Visualization": Visulization
}