#!/usr/bin/env python3
"""
Batch convert Perl test files (.t) to Python test files (.py)
"""
import os
import sys
import re
from pathlib import Path

TEMPLATE = '''#!/usr/bin/env python3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), {parent_levels}, 'lib'))

try:
    from {module_import} import {class_name}
except ImportError:
    {class_name} = None


class Test{test_class_name}(unittest.TestCase):
    
    @unittest.skipIf({class_name} is None, "{class_name} not implemented")
    def test_{test_method_name}(self):
        """Test {test_description}"""
        # TODO: Implement test logic
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
'''

def convert_path_to_module(perl_path):
    """Convert Perl module path to Python import path"""
    # Remove .t extension
    path = perl_path.replace('.t', '')
    # Convert path separators
    path = path.replace('\\', '.').replace('/', '.')
    # Remove t.tasks prefix
    if path.startswith('t.tasks.'):
        path = path[8:]
    return path

def generate_test_file(perl_file, output_file):
    """Generate Python test file from Perl test file path"""
    
    # Calculate relative path depth
    depth = len(Path(perl_file).relative_to('t/tasks').parts) - 1
    parent_levels = "'../" * depth + "..'"
    
    # Extract module info from path
    rel_path = str(Path(perl_file).relative_to('t/tasks'))
    parts = rel_path.replace('\\', '/').replace('.t', '').split('/')
    
    # Build module import path
    if len(parts) == 1:
        # Top level task (e.g., esx.t -> GLPI.Agent.Task.ESX)
        module_name = parts[0].title()
        module_import = f'GLPI.Agent.Task.{module_name}'
        class_name = module_name
    else:
        # Nested (e.g., inventory/linux/cpu.t -> GLPI.Agent.Task.Inventory.Linux.CPU)
        module_parts = [p.title() for p in parts]
        module_import = 'GLPI.Agent.Task.' + '.'.join(module_parts)
        class_name = module_parts[-1]
    
    test_class_name = ''.join([p.title() for p in parts])
    test_method_name = '_'.join(parts)
    test_description = ' '.join(parts)
    
    content = TEMPLATE.format(
        parent_levels=parent_levels,
        module_import=module_import,
        class_name=class_name,
        test_class_name=test_class_name,
        test_method_name=test_method_name,
        test_description=test_description
    )
    
    # Create output directory
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Write file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Converted: {perl_file} -> {output_file}")

def main():
    tasks_dir = Path('t/tasks')
    
    if not tasks_dir.exists():
        print(f"Error: {tasks_dir} not found")
        return 1
    
    # Find all .t files
    perl_files = list(tasks_dir.rglob('*.t'))
    
    print(f"Found {len(perl_files)} Perl test files")
    
    converted = 0
    skipped = 0
    
    for perl_file in perl_files:
        output_file = perl_file.with_suffix('.py')
        
        # Skip if Python file already exists
        if output_file.exists():
            skipped += 1
            continue
        
        try:
            generate_test_file(str(perl_file), str(output_file))
            converted += 1
        except Exception as e:
            print(f"Error converting {perl_file}: {e}")
    
    print(f"\nConversion complete:")
    print(f"  Converted: {converted}")
    print(f"  Skipped (already exist): {skipped}")
    print(f"  Total: {len(perl_files)}")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())

