import ast
import sys
import os

def test_pyscript_app_syntax():
    """
    Verifies that pyscript_app/main.py has valid Python syntax.
    This catches IndentationErrors and SyntaxErrors.
    """
    app_path = os.path.join(os.path.dirname(__file__), '..', 'main.py')
    
    print(f"Testing syntax of {app_path}...")
    
    try:
        with open(app_path, 'r') as f:
            content = f.read()
        
        # specific check for the known indentation issue
        if "def show_stats_handler(event):" not in content:
             # It might be indented, but let's check if it exists at top level in AST
             pass

        # Parse the code into an AST
        tree = ast.parse(content, filename=app_path)
        
        print("✅ Syntax is valid.")
        
        # verify critical functions exist
        required_functions = [
            'init',
            'show_stats_handler',
            'save_score_handler', 
            'render_courts',
            'start_session_handler'
        ]
        
        found_functions = set()
        
        # The file structure is a bit complex with try/except blocks.
        # We need to walk the tree.
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                found_functions.add(node.name)
                
        missing = [func for func in required_functions if func not in found_functions]
        
        if missing:
            print(f"❌ Missing critical functions: {missing}")
            sys.exit(1)
        else:
            print(f"✅ All critical functions found: {required_functions}")

    except SyntaxError as e:
        print(f"❌ Syntax Error: {e}")
        print(f"Line {e.lineno}: {e.text.strip() if e.text else ''}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_pyscript_app_syntax()
