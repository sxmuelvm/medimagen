"""Chequeo de salud para Docker. No revela datos ni toca la base."""
from flask import Blueprint, jsonify

bp = Blueprint("salud", __name__)


@bp.get("/salud")
def salud():
    return jsonify({"estado": "ok"}), 200