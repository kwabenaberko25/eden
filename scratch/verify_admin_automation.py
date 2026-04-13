import os
import sys
import shutil
from pathlib import Path
import unittest

# Add framework to path
sys.path.insert(0, str(Path(os.getcwd())))

class TestAdminAutomation(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path("scratch/test_project")
        if self.tmp_dir.exists():
            shutil.rmtree(self.tmp_dir)
        self.tmp_dir.mkdir(parents=True)
        
        # Create a package
        (self.tmp_dir / "__init__.py").write_text("")
        (self.tmp_dir / "app").mkdir()
        (self.tmp_dir / "app" / "__init__.py").write_text("")
        
        # Create models.py
        models_content = """from eden.db import Model, StringField
class AutoDiscoveredModel(Model):
    name: str = StringField()
"""
        (self.tmp_dir / "app" / "models.py").write_text(models_content)
        
    def tearDown(self):
        if self.tmp_dir.exists():
            shutil.rmtree(self.tmp_dir)
            
    def test_discovery(self):
        from eden.db.discovery import discover_models
        from eden.db import get_models
        from eden.admin import admin
        
        # Change CWD to the test project so discovery finds it
        old_cwd = os.getcwd()
        os.chdir(self.tmp_dir)
        try:
            # Ensure sys.path includes the current directory
            if str(self.tmp_dir) not in sys.path:
                sys.path.insert(0, str(self.tmp_dir))
                
            # Run discovery
            discover_models()
            
            # Check if model is found
            models = get_models()
            model_names = [m.__name__ for m in models]
            print(f"Discovered models: {model_names}")
            self.assertIn("AutoDiscoveredModel", model_names)
            
            # Check if admin auto-discovery works
            admin.auto_discover()
            registered_models = [m.__name__ for m in admin._registry.keys()]
            print(f"Admin registered models: {registered_models}")
            self.assertIn("AutoDiscoveredModel", registered_models)
            
        finally:
            os.chdir(old_cwd)

if __name__ == "__main__":
    unittest.main()
