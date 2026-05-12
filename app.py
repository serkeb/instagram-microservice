from flask import Flask, jsonify, request
from instagrapi import Client
import os, threading, time, traceback

app = Flask(__name__)
_cl = None
_lock = threading.Lock()

_cache = {}
CACHE_TTL = 300

def cached(key, fn):
    now = time.time()
    if key in _cache and now - _cache[key]["ts"] < CACHE_TTL:
        return _cache[key]["data"]
    result = fn()
    _cache[key] = {"data": result, "ts": now}
    return result

def get_client():
    global _cl
    with _lock:
        if _cl is None:
            _cl = Client()
            _cl.delay_range = [3, 6]
            _cl.request_timeout = 30
            _cl.login(os.environ["IG_USER"], os.environ["IG_PASS"])
    return _cl

@app.route("/profile/<username>")
def profile(username):
    try:
        def fetch():
            cl = get_client()
            uid = cl.user_id_from_username(username)
            user = cl.user_info(uid)
            return {
                "username": user.username or "",
                "full_name": user.full_name or "",
                "followers": user.follower_count or 0,
                "following": user.following_count or 0,
                "posts": user.media_count or 0,
                "bio": user.biography or "",
                "is_private": user.is_private,
                "profile_pic": str(user.profile_pic_url) if user.profile_pic_url else None
            }
        return jsonify(cached(f"profile:{username}", fetch))
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/reels/<username>")
def reels(username):
    limit = request.args.get("limit", 20, type=int)
    sort_by = request.args.get("sort", "recent")
    try:
        def fetch():
            cl = get_client()
            uid = cl.user_id_from_username(username)
            medias = cl.user_clips(uid, amount=limit)
            data = [{
                "id": str(m.pk),
                "caption": m.caption_text or "",
                "likes": m.like_count or 0,
                "views": m.view_count or 0,
                "comments": m.comment_count or 0,
                "date": m.taken_at.isoformat() if m.taken_at else None,
                "video_url": str(m.video_url) if m.video_url else None,
                "thumbnail": str(m.thumbnail_url) if m.thumbnail_url else None,
            } for m in medias]
            if sort_by == "likes":
                data.sort(key=lambda x: x["likes"], reverse=True)
            elif sort_by == "views":
                data.sort(key=lambda x: x["views"], reverse=True)
            return data
        return jsonify(cached(f"reels:{username}:{sort_by}", fetch))
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/posts/<username>")
def posts(username):
    limit = request.args.get("limit", 20, type=int)
    sort_by = request.args.get("sort", "recent")
    try:
        def fetch():
            cl = get_client()
            uid = cl.user_id_from_username(username)
            medias = cl.user_medias(uid, amount=limit)
            data = [{
                "id": str(m.pk),
                "caption": m.caption_text or "",
                "likes": m.like_count or 0,
                "comments": m.comment_count or 0,
                "date": m.taken_at.isoformat() if m.taken_at else None,
                "media_type": m.media_type,
                "thumbnail": str(m.thumbnail_url) if m.thumbnail_url else None,
                "video_url": str(m.video_url) if m.video_url else None,
            } for m in medias]
            if sort_by == "likes":
                data.sort(key=lambda x: x["likes"], reverse=True)
            return data
        return jsonify(cached(f"posts:{username}:{sort_by}", fetch))
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
