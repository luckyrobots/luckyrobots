import os
import site
import shutil
import subprocess
import sys
import ast

def get_source_directory():
    # Start from the directory of the script being run
    current_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    
    while current_dir != os.path.dirname(current_dir):  # Stop at root directory
        setup_py_path = os.path.join(current_dir, 'setup.py')
        if os.path.exists(setup_py_path):
            with open(setup_py_path, 'r') as f:
                content = f.read()
            
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call) and getattr(node.func, 'id', '') == 'setup':
                        for keyword in node.keywords:
                            if keyword.arg == 'name' and keyword.value.s == 'luckyrobots':
                                return current_dir
            except SyntaxError:
                pass  # If the file is not valid Python, continue searching
        
        current_dir = os.path.dirname(current_dir)
    
    print("Could not find a setup.py file with name='luckyrobots'. This likely means you haven't cloned the repository. To use this feature, please clone the repository and run the command with the --lr-library-dev flag from within the cloned directory.")
    sys.exit(1)

def library_dev():
    
    if "--lr-library-dev" not in sys.argv:
        print("If you want to help with developing this library, run with --lr-library-dev argument.")
        return 
    else:
        print("--------------------------------------------------------------------------------")
        print("This will create a symbolic link to the src/luckyrobots directory in your pip installation directory.")
        print("This is useful if you want to test your local changes without having to reinstall the package.")
        print("Then you can push your branch and create a pull request.")
        print("--------------------------------------------------------------------------------")     
        # Discover where pip is installing its modules
        # Ask user for confirmation
        pip_path = site.getsitepackages()[0]
        luckyrobots_pip_path = os.path.join(pip_path, "luckyrobots")
        luckyrobots_dev_dir = os.path.join(get_source_directory(), "src", "luckyrobots")

        

        # print(f"Absolute path of luckyrobots directory: {luckyrobots_dir}")
        print("Creating symlink between:")
        print(f"src_path: {luckyrobots_dev_dir}, luckyrobots_path: {luckyrobots_pip_path}")

        input("Press Enter to continue or Ctrl+C to cancel...")
        # Check if the pip_path exists
        if os.path.isdir(pip_path):
            print(f"Pip installation path found: {pip_path}")


            # Remove existing luckyrobots directory or symlink if it exists
            if os.path.exists(luckyrobots_pip_path):
                print("Removing existing luckyrobots directory or symlink...")
                if os.path.islink(luckyrobots_pip_path):
                    os.unlink(luckyrobots_pip_path)
                else:
                    shutil.rmtree(luckyrobots_pip_path)
            try:
                os.symlink(luckyrobots_dev_dir, luckyrobots_pip_path)
                print("Symbolic link created successfully. Your local luckyrobots package is now used.")
                print("Remember, if you change your virtual environment, you need to run this script again.")
            except OSError as e:
                print(f"Error: Failed to create symbolic link. {e}")
                sys.exit(1)
        else:
            print("Error: Pip installation path not found.")
            sys.exit(1)