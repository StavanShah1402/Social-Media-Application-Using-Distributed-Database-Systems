from flask import Flask, render_template, request, jsonify, redirect
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import uuid
import jwt
from functools import wraps
from flask import Flask, request, jsonify, render_template, redirect, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import uuid
import jwt
from functools import wraps
# Secret for JWT token signing
SECRET_KEY = "your_secret_key"
app = Flask(__name__)

# MongoDB setup
client = MongoClient("mongodb+srv://test1234:test1234@cluster0.wsbge.mongodb.net/")
db = client["socialMedia"]
users_collection = db["users"]
posts_collection = db["posts"]
messages_collection = db["messages"]
comments_collection = db["comments"]

def serialize_mongo_doc(doc):
    """Convert ObjectId and other non-serializable types in a MongoDB document."""
    if not doc:
        return doc
    doc["_id"] = str(doc["_id"])  # Convert ObjectId to string
    return doc

# Middleware to verify the token
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get('token')  # Get token from cookies
        if not token:
            return jsonify({"error": "Token is missing!"}), 401
        
        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            request.user_id = data["user_id"]
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired!"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token!"}), 401

        return f(*args, **kwargs)
    return decorated


# Route for signup
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')  # Render signup form

    try:
        data = request.form  # Use form data from HTML
        username = data.get('username')
        email = data.get('email')
        password = generate_password_hash(data.get('password'))

        # Check if username exists
        if users_collection.find_one({"username": username}):
            return jsonify({"error": "Username already exists!"}), 409

        user_id = str(uuid.uuid4())
        users_collection.insert_one({
            "user_id": user_id,
            "username": username,
            "email": email,
            "password": password,
            "profile_picture": "https://example.com/default_profile.jpg",
            "bio": "New user",
            "created_at": datetime.now(),
            "followers": [],
            "following": []
        })

        return redirect(url_for('login'))  # Redirect to login page after successful signup
    except Exception as e:
        # Log the error for debugging
        print(f"Error during signup: {e}")
        return jsonify({"error": "Internal server error!"}), 500


# Route for login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')  # Render login form

    data = request.form  # Use form data from HTML
    username = data.get('username')
    password = data.get('password')

    user = users_collection.find_one({"username": username})
    if user and check_password_hash(user["password"], password):
        token = jwt.encode(
            {
                "user_id": str(user["user_id"]),
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            SECRET_KEY,
            algorithm="HS256"
        )
        print(token)
        response = redirect(url_for('feed'))  # Redirect to the feed
        response.set_cookie('token', token, httponly=True, max_age=3600)  # Set the token as a secure cookie
        return response

    return jsonify({"error": "Invalid username or password!"}), 401



# Protected route: Feed
@app.route('/feed', methods=['GET'])
@token_required
def feed():
    current_user_id = request.user_id  # Extract the logged-in user's ID from the token
    token = request.cookies.get('token')  # Get the token from cookies

    # Fetch posts from users the current user follows
    user = users_collection.find_one({"user_id": current_user_id}, {"following": 1})
    following = user.get("following", []) if user else []
    following.append(current_user_id)  # Include the user's own posts

    # Pagination parameters
    page = int(request.args.get('page', 1))
    per_page = 10

    # Fetch paginated posts
    posts = list(
        posts_collection.find({"user_id": {"$in": following}})
        .sort("timestamp", -1)
        .skip((page - 1) * per_page)
        .limit(per_page)
    )
    print("Posts fetched for feed:")
    print([post.get("media") for post in posts])
    # Serialize posts for the template
    serialized_posts = [serialize_mongo_doc(post) for post in posts]

    # Render feed.html and pass the current_user_id
    return render_template(
        'feed.html',
        posts=serialized_posts,
        token=token,
        current_user_id=current_user_id,
        page=page
    )



@app.route('/search', methods=['GET'])
@token_required
def search():
    current_user_id = request.user_id
    query = request.args.get('q', '').strip()  # Get the search query from the URL
    token = request.cookies.get('token')  # Get the token from cookies

    # Search users by username
    if query:
        users = list(users_collection.find(
            {"username": {"$regex": query, "$options": "i"}},  # Case-insensitive search
            {"user_id": 1, "username": 1}  # Only fetch user_id and username
        ))
    else:
        users = []

    # Fetch top 5 liked posts
    top_posts = list(posts_collection.find().sort([("likes", -1)]).limit(5))  # Sort by likes descending

    # Serialize data for rendering
    serialized_users = [serialize_mongo_doc(user) for user in users]
    serialized_posts = [serialize_mongo_doc(post) for post in top_posts]

    # Render the search.html template with the search results and top posts
    return render_template(
        'search.html',
        query=query,
        users=serialized_users,
        top_posts=serialized_posts,
        token=token,
        current_user_id=current_user_id
    )
@app.route('/profile/<user_id>', methods=['GET'])
@token_required
def profile(user_id):
    current_user_id = request.user_id  # Extract the logged-in user's ID from the token

    # Fetch the profile user
    user = users_collection.find_one({"user_id": user_id})
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Fetch the user's posts
    posts = list(posts_collection.find({"user_id": user_id}).sort("timestamp", -1))

    # Serialize user and posts
    user_data = serialize_mongo_doc(user)
    serialized_posts = [serialize_mongo_doc(post) for post in posts]

    # Count followers and following
    followers_count = len(user_data.get("followers", []))
    following_count = len(user_data.get("following", []))

    # Check if the logged-in user is following the profile user
    is_following = current_user_id in user_data.get("followers", [])

    # Render the profile page
    return render_template(
        'profile.html',
        user=user_data,
        posts=serialized_posts,
        followers_count=followers_count,
        following_count=following_count,
        is_following=is_following,
        current_user_id=current_user_id
    )

@app.route('/follow/<target_user_id>', methods=['POST'])
@token_required
def follow_user(target_user_id):
    current_user_id = request.user_id

    # Add the current user to the target user's followers
    users_collection.update_one(
        {"user_id": target_user_id},
        {"$addToSet": {"followers": current_user_id}}
    )

    # Add the target user to the current user's following
    users_collection.update_one(
        {"user_id": current_user_id},
        {"$addToSet": {"following": target_user_id}}
    )

    return redirect(url_for('profile', user_id=target_user_id))
@app.route('/unfollow/<target_user_id>', methods=['POST'])
@token_required
def unfollow_user(target_user_id):
    current_user_id = request.user_id

    # Remove the current user from the target user's followers
    users_collection.update_one(
        {"user_id": target_user_id},
        {"$pull": {"followers": current_user_id}}
    )

    # Remove the target user from the current user's following
    users_collection.update_one(
        {"user_id": current_user_id},
        {"$pull": {"following": target_user_id}}
    )

    return redirect(url_for('profile', user_id=target_user_id))


# Protected route: Create post
# Protected route: Create post
@app.route('/create_post', methods=['POST'])
@token_required
def create_post():
    user_id = request.user_id
    data = request.get_json()

    heading = data.get("heading", "").strip()
    content = data.get("content", "").strip()
    media = data.get("media", "")

    if not heading or not content:
        return jsonify({"error": "Heading and content are required!"}), 400

    post = {
        "post_id": str(uuid.uuid4()),
        "user_id": user_id,
        "heading": heading,
        "content": content,
        "media": media or "https://example.com/default_media.jpg",
        "timestamp": datetime.now(),
        "likes": [],
        "comments": []
    }

    # Insert the post into the database
    result = posts_collection.insert_one(post)

    # Add the MongoDB-generated _id as a string to the response
    post["_id"] = str(result.inserted_id)

    return jsonify({"message": "Post created successfully!", "post": post}), 201


# Protected route: Add comment to a post
@app.route('/post/<post_id>/comment', methods=['POST'])
@token_required
def add_comment(post_id):
    user_id = request.user_id
    data = request.get_json()
    comment_text = data.get('comment_text', "").strip()

    if not comment_text:
        return jsonify({"error": "Comment cannot be empty!"}), 400

    comment = {
        "comment_id": str(uuid.uuid4()),
        "post_id": post_id,
        "user_id": user_id,
        "content": comment_text,
        "timestamp": datetime.now()
    }

    comments_collection.insert_one(comment)
    return jsonify({"message": "Comment added successfully!"}), 201

# Protected route: Like a post
@app.route('/post/<post_id>/like', methods=['POST'])
@token_required
def like_post(post_id):
    user_id = request.user_id
    action = request.get_json().get('action')

    if action == 'like':
        posts_collection.update_one(
            {"_id": ObjectId(post_id)},
            {"$addToSet": {"likes": user_id}}
        )
    elif action == 'unlike':
        posts_collection.update_one(
            {"_id": ObjectId(post_id)},
            {"$pull": {"likes": user_id}}
        )
    else:
        return jsonify({"error": "Invalid action!"}), 400

    return jsonify({"message": f"Post {action}d successfully!"}), 200

@app.route('/send_message/<conversation_id>', methods=['POST'])
@token_required
def send_message(conversation_id):
    user_id = request.user_id  # Extracted from the token by @token_required

    # Use form data instead of JSON payload
    receiver_id = request.form.get('receiver_id')
    message = request.form.get('message')

    if not receiver_id or not message:
        return jsonify({"error": "Receiver ID and message are required!"}), 400

    # Insert the message into the database
    messages_collection.insert_one({
        "conversation_id": conversation_id,
        "sender_id": user_id,
        "receiver_id": receiver_id,
        "message": message,
        "timestamp": datetime.now()
    })

    return redirect(url_for('messages', conversation_id=conversation_id))



# Protected route: View messages
@app.route('/messages', methods=['GET', 'POST'])
@token_required
def messages():
    user_id = request.user_id
    token = request.cookies.get('token')  # Get the token for the hamburger menu

    # Fetch all conversations for the user
    conversations = list(messages_collection.aggregate([
        {
            "$match": {
                "$or": [
                    {"sender_id": user_id},
                    {"receiver_id": user_id}
                ]
            }
        },
        {
            "$group": {
                "_id": "$conversation_id",
                "participant": {"$last": {"$cond": [{"$ne": ["$sender_id", user_id]}, "$sender_id", "$receiver_id"]}},
                "last_message": {"$last": "$message"},
                "timestamp": {"$last": "$timestamp"}
            }
        },
        {"$sort": {"timestamp": -1}}
    ]))

    # Serialize conversations
    serialized_conversations = [{
        "conversation_id": conv["_id"],
        "participant": conv["participant"],
        "last_message": conv["last_message"],
        "timestamp": conv["timestamp"].isoformat() if conv["timestamp"] else None
    } for conv in conversations]

    # Get the selected conversation ID from the query string
    selected_conversation_id = request.args.get('conversation_id')
    selected_messages = []

    if selected_conversation_id:
        # Fetch messages for the selected conversation
        selected_messages = list(messages_collection.find(
            {"conversation_id": selected_conversation_id}
        ).sort("timestamp", 1))  # Sort messages in ascending order

        # Serialize messages
        selected_messages = [{
            "sender_id": msg["sender_id"],
            "receiver_id": msg["receiver_id"],
            "message": msg["message"],
            "timestamp": msg["timestamp"].isoformat() if msg["timestamp"] else None
        } for msg in selected_messages]

    # Render the `messages.html` template
    return render_template(
        'messages.html',
        conversations=serialized_conversations,
        messages=selected_messages,
        selected_conversation_id=selected_conversation_id,
        token=token,
        current_user_id=user_id
    )



# Logout (optional for JWT, as tokens are stateless)
@app.route('/logout', methods=['POST'])
@token_required
def logout():
    response = redirect(url_for('login'))  # Redirect to the login page
    response.delete_cookie('token')  # Remove the token cookie
    return response


if __name__ == "__main__":
    app.run(debug=True, port=5000)