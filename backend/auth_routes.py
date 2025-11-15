# from flask import Blueprint, request, jsonify, redirect
# from werkzeug.security import generate_password_hash, check_password_hash
# from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
# import datetime
# import os
# import urllib.parse
# import requests
# from db import users_collection
# from config import Config

# auth_bp = Blueprint("auth", __name__)

# # ---------- REGISTER ----------
# @auth_bp.route('/register', methods=['POST'])
# def register():
#     data = request.get_json()
#     username = data.get("username")
#     email = data.get("email")
#     password = data.get("password")

#     if users_collection.find_one({"email": email}):
#         return jsonify({"msg": "User already exists"}), 400

#     hashed_pw = generate_password_hash(password)
#     users_collection.insert_one({
#         "username": username,
#         "email": email,
#         "password": hashed_pw,
#         "createdAt": datetime.datetime.utcnow()
#     })

#     return jsonify({"msg": "Registered successfully"}), 201


# # ---------- LOGIN ----------
# @auth_bp.route('/login', methods=['POST'])
# def login():
#     data = request.get_json()
#     email = data.get("email")
#     password = data.get("password")

#     user = users_collection.find_one({"email": email})
#     if not user or not check_password_hash(user["password"], password):
#         return jsonify({"msg": "Invalid email or password"}), 401

#     # Create JWT token using flask_jwt_extended
#     token = create_access_token(
#         identity=str(user["_id"]), 
#         additional_claims={"username": user["username"]},
#         expires_delta=datetime.timedelta(hours=1)  # 1 hr expiry
#     )

#     return jsonify({"token": token}), 200


# # ---------- GOOGLE OAUTH ----------
# @auth_bp.route('/google/login', methods=['GET'])
# def google_login():
#     client_id = Config.GOOGLE_CLIENT_ID
#     redirect_uri = Config.GOOGLE_REDIRECT_URI
#     scope = 'openid email profile'
#     auth_uri = Config.GOOGLE_AUTH_URI
#     state = request.args.get('state', 'state')

#     params = {
#         'client_id': client_id,
#         'redirect_uri': redirect_uri,
#         'response_type': 'code',
#         'scope': scope,
#         'access_type': 'offline',
#         'prompt': 'consent',
#         'state': state,
#     }
#     url = f"{auth_uri}?{urllib.parse.urlencode(params)}"
#     return jsonify({"auth_url": url})


# @auth_bp.route('/google/callback', methods=['GET'])
# def google_callback():
#     # This route is unused if redirect goes to frontend. Keeping for completeness if backend callback is configured.
#     code = request.args.get('code')
#     error = request.args.get('error')
#     if error:
#         # Redirect back to frontend with error
#         dest = f"{Config.FRONTEND_BASE}/auth/callback?error={urllib.parse.quote(error)}"
#         return redirect(dest)
#     if not code:
#         return jsonify({"msg": "Missing code"}), 400

#     token_data = {
#         'code': code,
#         'client_id': Config.GOOGLE_CLIENT_ID,
#         'client_secret': Config.GOOGLE_CLIENT_SECRET,
#         'redirect_uri': Config.GOOGLE_REDIRECT_URI,
#         'grant_type': 'authorization_code'
#     }
#     token_resp = requests.post(Config.GOOGLE_TOKEN_URI, data=token_data, headers={'Content-Type': 'application/x-www-form-urlencoded'})
#     if token_resp.status_code != 200:
#         dest = f"{Config.FRONTEND_BASE}/auth/callback?error=token_exchange_failed"
#         return redirect(dest)

#     tokens = token_resp.json()
#     access_token = tokens.get('access_token')
#     if not access_token:
#         dest = f"{Config.FRONTEND_BASE}/auth/callback?error=no_access_token"
#         return redirect(dest)

#     userinfo_resp = requests.get(Config.GOOGLE_USERINFO_URI, headers={'Authorization': f'Bearer {access_token}'})
#     if userinfo_resp.status_code != 200:
#         dest = f"{Config.FRONTEND_BASE}/auth/callback?error=userinfo_failed"
#         return redirect(dest)

#     info = userinfo_resp.json()
#     email = info.get('email')
#     name = info.get('name') or info.get('given_name') or 'User'
#     if not email:
#         dest = f"{Config.FRONTEND_BASE}/auth/callback?error=no_email"
#         return redirect(dest)

#     # Upsert user
#     user = users_collection.find_one({"email": email})
#     if not user:
#         users_collection.insert_one({
#             "username": name,
#             "email": email,
#             "password": None,
#             "provider": "google",
#             "createdAt": datetime.datetime.utcnow()
#         })
#         user = users_collection.find_one({"email": email})

#     token = create_access_token(identity=str(user["_id"]), additional_claims={"username": user.get("username", name)})

#     # Redirect back to frontend with token
#     dest = f"{Config.FRONTEND_BASE}/auth/callback?token={urllib.parse.quote(token)}"
#     return redirect(dest)
