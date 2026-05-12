from flask import Flask, jsonify, request
from instagrapi import Client
import os, threading

app = Flask(__name__)
_cl = None
_lock = threading.Lock()

def get_client():
    global _cl
    with _lock:
        if _cl is None:
            _cl = Client()
            _cl.delay_range = [2, 4]
            _cl.login(os.environ["IG_USER"], os.environ["IG_PASS"])
    return _cl

@app.route("/profile/<username>")
def profile(username):
    try:
        cl = get_client()
        user = cl.user_info_by_username(username)
        return jsonify({
            "username": user.username,
            "full_name": user.full_name,
            "followers": user.follower_count,
            "following": user.following_count,
            "posts": user.media_count,
            "bio": user.biography,
            "profile_pic": str(user.profile_pic_url)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/reels/<username>")
def reels(username):
    limit = request.args.get("limit", 20, type=int)
    sort_by = request.args.get("sort", "recent")
    try:
        cl = get_client()
        user_id = cl.user_id_from_username(username)
        medias = cl.user_clips(user_id, amount=limit)
        data = [{
            "id": str(m.pk),
            "caption": m.caption_text,
            "likes": m.like_count,
            "views": m.view_count,
            "comments": m.comment_count,
            "date": m.taken_at.isoformat(),
            "video_url": str(m.video_url),
            "thumbnail": str(m.thumbnail_url),
        } for m in medias]

        if sort_by == "likes":
            data.sort(key=lambda x: x["likes"] or 0, reverse=True)
        elif sort_by == "views":
            data.sort(key=lambda x: x["views"] or 0, reverse=True)

        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)