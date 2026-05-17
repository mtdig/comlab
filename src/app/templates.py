from fastapi.templating import Jinja2Templates

from app.config import ROOT_PATH, TEMPLATES_DIR

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals["root_path"] = ROOT_PATH
