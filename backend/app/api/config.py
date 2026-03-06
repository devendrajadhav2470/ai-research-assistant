"""Config API endpoints"""

import logging
from flask import Blueprint, jsonify
import os
from dotenv import load_dotenv
logger = logging.getLogger(__name__)

config_bp = Blueprint("config", __name__)

load_dotenv()

@config_bp.route("/defaults", methods=["GET"])
def get_defaults():

    default_model = os.environ.get("DEFAULT_MODEL_NAME")
    default_model_provider = os.environ.get("DEFAULT_LLM_PROVIDER")
    if(not default_model):
        return jsonify({"error": "default model not set"}), 404
    if(not default_model_provider):
        return jsonify({"error": "default model provider not set"}), 404

    return jsonify({
        "default_model": default_model,
        "default_model_provider": default_model_provider
    })