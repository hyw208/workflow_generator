
import pandas as pd

def parse_workflows_excel(file_path):
    """
    Parses a multi-sheet Excel file and returns a dictionary of DataFrames.

    Args:
        file_path (str): The path to the Excel file.

    Returns:
        dict: A dictionary where keys are sheet names and values are pandas DataFrames.
              Returns an empty dictionary if the file cannot be read.
    """
    try:
        xls = pd.ExcelFile(file_path)
        sheet_names = xls.sheet_names
        
        dataframes = {sheet: pd.read_excel(xls, sheet_name=sheet) for sheet in sheet_names}
        
        return dataframes

    except FileNotFoundError:
        print(f"Error: The file at {file_path} was not found.")
        return {}
    except Exception as e:
        print(f"An error occurred: {e}")
        return {}

if __name__ == '__main__':
    # Example usage:
    file_to_parse = 'workflows.xlsx'
    parsed_data = parse_workflows_excel(file_to_parse)

    if parsed_data:
        print(f"Successfully parsed {len(parsed_data)} sheets into a dictionary of dataframes.")
        for name, df in parsed_data.items():
            print(f"\nDataFrame from Sheet '{name}':")
            print(df.head())
