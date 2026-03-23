import uvicorn

from api import agent_api

uvicorn.run(agent_api.app)