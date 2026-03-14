# Community Comments - Complete API Guide

Comprehensive documentation for the community comments system including nested replies, liking, and user information.

---

## Table of Contents

1. [Overview](#overview)
2. [Get Comments (Nested Structure)](#get-comments-nested-structure)
3. [Create Comment](#create-comment)
4. [Like Comment](#like-comment)
5. [Unlike Comment](#unlike-comment)
6. [Frontend Implementation](#frontend-implementation)
7. [Database Setup](#database-setup)

---

## Overview

The comments system supports:
- ✅ **Nested replies** - Comments can reply to other comments
- ✅ **User information** - Username and avatar includeda
- ✅ **Like system** - Users can like comments
- ✅ **Like status** - Shows if current user has liked
- ✅ **Threaded display** - Hierarchical structure for easy rendering
- ✅ **Optional auth** - Works for guests, enhanced for logged-in users

### Key Features

| Feature | Guest Users | Authenticated Users |
|---------|-------------|---------------------|
| View comments | ✅ Yes | ✅ Yes |
| View replies | ✅ Yes | ✅ Yes |
| See like counts | ✅ Yes | ✅ Yes |
| See like status | ❌ No | ✅ Yes |
| Create comments | ❌ No | ✅ Yes |
| Like comments | ❌ No | ✅ Yes |

---

## Get Comments (Nested Structure)

Get all comments for a post with nested replies in a hierarchical structure.

### Endpoint
```
GET /api/v1/communities/posts/{post_id}/comments
```

### Authentication
**Optional** - Works without auth, includes `user_has_liked` if authenticated

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `post_id` | UUID | Yes | Post identifier |

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number (min: 1) |
| `limit` | integer | 50 | Top-level comments per page (min: 1, max: 100) |

### Response Structure

```typescript
interface CommentsResponse {
  comments: Comment[];        // Top-level comments with nested replies
  total: number;             // Total top-level comments
  total_with_replies: number; // Total comments including all replies
  page: number;
  limit: number;
}

interface Comment {
  id: string;
  post_id: string;
  author_id: string;
  author_username: string;
  author_avatar: string;
  content: string;
  parent_id: string | null;
  likes: number;
  user_has_liked: boolean;
  replies: Comment[];        // Nested replies (recursive)
  created_at: string;
}
```

### Example Response

```json
{
  "comments": [
    {
      "id": "comment-1",
      "post_id": "post-uuid",
      "author_id": "user-1",
      "author_username": "john_artist",
      "author_avatar": "👨‍🎨",
      "content": "Amazing work! How long did this take?",
      "parent_id": null,
      "likes": 12,
      "user_has_liked": true,
      "created_at": "2026-02-22T10:00:00.000Z",
      "replies": [
        {
          "id": "comment-2",
          "post_id": "post-uuid",
          "author_id": "user-2",
          "author_username": "jane_3d",
          "author_avatar": "👩‍💻",
          "content": "Thanks! About 3 weeks of work.",
          "parent_id": "comment-1",
          "likes": 5,
          "user_has_liked": false,
          "created_at": "2026-02-22T10:15:00.000Z",
          "replies": [
            {
              "id": "comment-3",
              "post_id": "post-uuid",
              "author_id": "user-1",
              "author_username": "john_artist",
              "author_avatar": "👨‍🎨",
              "content": "Wow, impressive dedication!",
              "parent_id": "comment-2",
              "likes": 2,
              "user_has_liked": true,
              "created_at": "2026-02-22T10:20:00.000Z",
              "replies": []
            }
          ]
        },
        {
          "id": "comment-4",
          "post_id": "post-uuid",
          "author_id": "user-3",
          "author_username": "mike_blender",
          "author_avatar": "🧑‍🎨",
          "content": "I'd love to see a tutorial on this!",
          "parent_id": "comment-1",
          "likes": 8,
          "user_has_liked": false,
          "created_at": "2026-02-22T10:30:00.000Z",
          "replies": []
        }
      ]
    },
    {
      "id": "comment-5",
      "post_id": "post-uuid",
      "author_id": "user-4",
      "author_username": "sarah_designer",
      "author_avatar": "👩‍🎨",
      "content": "The lighting is perfect!",
      "parent_id": null,
      "likes": 7,
      "user_has_liked": false,
      "created_at": "2026-02-22T09:45:00.000Z",
      "replies": []
    }
  ],
  "total": 2,
  "total_with_replies": 5,
  "page": 1,
  "limit": 50
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `comments` | array | Top-level comments with nested replies |
| `total` | integer | Total number of top-level comments |
| `total_with_replies` | integer | Total comments including all replies |
| `page` | integer | Current page number |
| `limit` | integer | Items per page |

#### Comment Object Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Comment identifier |
| `post_id` | UUID | Post identifier |
| `author_id` | UUID | Author's user ID |
| `author_username` | string | Author's username |
| `author_avatar` | string | Author's avatar (emoji or URL) |
| `content` | string | Comment text |
| `parent_id` | UUID\|null | Parent comment ID (null for top-level) |
| `likes` | integer | Total likes |
| `user_has_liked` | boolean | Whether current user liked (false if not authenticated) |
| `replies` | array | Nested reply comments (recursive) |
| `created_at` | datetime | Creation timestamp (ISO 8601) |

### cURL Examples

```bash
# Without authentication
curl -X GET "http://localhost:8000/api/v1/communities/posts/post-uuid/comments"

# With authentication (includes user_has_liked)
curl -X GET "http://localhost:8000/api/v1/communities/posts/post-uuid/comments" \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."

# With pagination
curl -X GET "http://localhost:8000/api/v1/communities/posts/post-uuid/comments?page=1&limit=20" \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

## Create Comment

Create a new comment or reply to an existing comment.

### Endpoint
```
POST /api/v1/communities/posts/{post_id}/comments
```

### Authentication
**Required**

### Headers
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

### Request Body

```json
{
  "content": "This is an amazing post!",
  "parent_id": null
}
```

#### For Replies

```json
{
  "content": "Thanks for the feedback!",
  "parent_id": "parent-comment-uuid"
}
```

### Request Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `content` | string | Yes | Comment text (max 1000 chars) |
| `parent_id` | UUID | No | Parent comment ID (null for top-level comment) |

### Success Response (201 Created)

Returns the created comment with user info.

---

## Like Comment

Like a comment to show appreciation.

### Endpoint
```
POST /api/v1/communities/comments/{comment_id}/like
```

### Authentication
**Required**

### Success Response (200 OK)
```json
{
  "message": "Comment liked successfully"
}
```

### Error Responses

```json
// 400 - Already liked
{
  "detail": "Comment already liked"
}

// 401 - Not authenticated
{
  "detail": "Could not validate credentials"
}
```

---

## Unlike Comment

Remove your like from a comment.

### Endpoint
```
DELETE /api/v1/communities/comments/{comment_id}/like
```

### Authentication
**Required**

### Success Response (200 OK)
```json
{
  "message": "Comment unliked successfully"
}
```

---

## Frontend Implementation

### React Component with Nested Comments

```typescript
import { useState, useEffect } from 'react';

interface Comment {
  id: string;
  author_username: string;
  author_avatar: string;
  content: string;
  likes: number;
  user_has_liked: boolean;
  replies: Comment[];
  created_at: string;
}

// Recursive comment component
function CommentItem({ 
  comment, 
  accessToken, 
  onLikeChange,
  depth = 0 
}: { 
  comment: Comment; 
  accessToken?: string;
  onLikeChange: () => void;
  depth?: number;
}) {
  const [isLiked, setIsLiked] = useState(comment.user_has_liked);
  const [likeCount, setLikeCount] = useState(comment.likes);
  const [showReplyForm, setShowReplyForm] = useState(false);
  
  const handleLike = async () => {
    if (!accessToken) {
      alert('Please login to like comments');
      return;
    }
    
    const method = isLiked ? 'DELETE' : 'POST';
    const response = await fetch(
      `http://localhost:8000/api/v1/communities/comments/${comment.id}/like`,
      {
        method,
        headers: { 'Authorization': `Bearer ${accessToken}` }
      }
    );
    
    if (response.ok) {
      setIsLiked(!isLiked);
      setLikeCount(prev => isLiked ? prev - 1 : prev + 1);
      onLikeChange();
    }
  };
  
  return (
    <div 
      className="comment-item" 
      style={{ marginLeft: `${depth * 2}rem` }}
    >
      {/* Comment header */}
      <div className="comment-header">
        <span className="avatar">{comment.author_avatar}</span>
        <span className="username">{comment.author_username}</span>
        <span className="time">
          {new Date(comment.created_at).toLocaleDateString()}
        </span>
      </div>
      
      {/* Comment content */}
      <p className="comment-content">{comment.content}</p>
      
      {/* Actions */}
      <div className="comment-actions">
        {accessToken ? (
          <button 
            onClick={handleLike}
            className={`like-btn ${isLiked ? 'liked' : ''}`}
          >
            {isLiked ? '❤️' : '🤍'} {likeCount > 0 && likeCount}
          </button>
        ) : (
          likeCount > 0 && <span>❤️ {likeCount}</span>
        )}
        
        {accessToken && (
          <button onClick={() => setShowReplyForm(!showReplyForm)}>
            Reply
          </button>
        )}
      </div>
      
      {/* Reply form */}
      {showReplyForm && (
        <ReplyForm 
          postId={comment.post_id}
          parentId={comment.id}
          accessToken={accessToken}
          onSuccess={() => {
            setShowReplyForm(false);
            onLikeChange(); // Refresh comments
          }}
        />
      )}
      
      {/* Nested replies */}
      {comment.replies.length > 0 && (
        <div className="replies">
          {comment.replies.map(reply => (
            <CommentItem
              key={reply.id}
              comment={reply}
              accessToken={accessToken}
              onLikeChange={onLikeChange}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// Main comments list component
function CommentsList({ postId, accessToken }: { postId: string; accessToken?: string }) {
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [totalWithReplies, setTotalWithReplies] = useState(0);
  
  const fetchComments = async () => {
    setLoading(true);
    
    const headers: HeadersInit = {};
    if (accessToken) {
      headers['Authorization'] = `Bearer ${accessToken}`;
    }
    
    const response = await fetch(
      `http://localhost:8000/api/v1/communities/posts/${postId}/comments`,
      { headers }
    );
    
    if (response.ok) {
      const data = await response.json();
      setComments(data.comments);
      setTotal(data.total);
      setTotalWithReplies(data.total_with_replies);
    }
    
    setLoading(false);
  };
  
  useEffect(() => {
    fetchComments();
  }, [postId, accessToken]);
  
  if (loading) return <div>Loading comments...</div>;
  
  return (
    <div className="comments-section">
      <h3>
        Comments ({total})
        {totalWithReplies > total && (
          <span className="reply-count">
            {' '}· {totalWithReplies - total} replies
          </span>
        )}
      </h3>
      
      {/* Comment form */}
      {accessToken && (
        <CommentForm 
          postId={postId}
          accessToken={accessToken}
          onSuccess={fetchComments}
        />
      )}
      
      {/* Comments list */}
      <div className="comments-list">
        {comments.map(comment => (
          <CommentItem
            key={comment.id}
            comment={comment}
            accessToken={accessToken}
            onLikeChange={fetchComments}
            depth={0}
          />
        ))}
      </div>
    </div>
  );
}
```

### CSS Styling

```css
.comments-section {
  margin-top: 2rem;
}

.comments-section h3 {
  font-size: 1.25rem;
  margin-bottom: 1rem;
}

.reply-count {
  font-size: 0.875rem;
  color: #666;
  font-weight: normal;
}

.comment-item {
  padding: 1rem;
  border-left: 2px solid #eee;
  margin-bottom: 0.5rem;
  transition: border-color 0.2s;
}

.comment-item:hover {
  border-left-color: #667eea;
}

.comment-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.avatar {
  font-size: 1.5rem;
}

.username {
  font-weight: 600;
  color: #333;
}

.time {
  font-size: 0.875rem;
  color: #666;
  margin-left: auto;
}

.comment-content {
  margin: 0.5rem 0;
  color: #444;
  line-height: 1.5;
}

.comment-actions {
  display: flex;
  gap: 1rem;
  margin-top: 0.5rem;
}

.like-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 0.875rem;
  color: #666;
  display: flex;
  align-items: center;
  gap: 0.25rem;
  transition: all 0.2s;
}

.like-btn:hover {
  color: #e74c3c;
  transform: scale(1.1);
}

.like-btn.liked {
  color: #e74c3c;
}

.replies {
  margin-top: 0.5rem;
}

/* Indentation for nested comments */
.comment-item[style*="margin-left"] {
  border-left-color: #ddd;
}
```

### Vanilla JavaScript Example

```javascript
// Recursive function to render comments
function renderComment(comment, depth = 0, accessToken) {
  const div = document.createElement('div');
  div.className = 'comment-item';
  div.style.marginLeft = `${depth * 2}rem`;
  
  div.innerHTML = `
    <div class="comment-header">
      <span class="avatar">${comment.author_avatar}</span>
      <span class="username">${comment.author_username}</span>
      <span class="time">${new Date(comment.created_at).toLocaleDateString()}</span>
    </div>
    <p class="comment-content">${comment.content}</p>
    <div class="comment-actions">
      ${accessToken ? `
        <button class="like-btn ${comment.user_has_liked ? 'liked' : ''}" 
                data-comment-id="${comment.id}"
                data-liked="${comment.user_has_liked}">
          ${comment.user_has_liked ? '❤️' : '🤍'} ${comment.likes > 0 ? comment.likes : ''}
        </button>
        <button class="reply-btn" data-comment-id="${comment.id}">Reply</button>
      ` : `
        ${comment.likes > 0 ? `<span>❤️ ${comment.likes}</span>` : ''}
      `}
    </div>
  `;
  
  // Render nested replies
  if (comment.replies && comment.replies.length > 0) {
    const repliesDiv = document.createElement('div');
    repliesDiv.className = 'replies';
    
    comment.replies.forEach(reply => {
      repliesDiv.appendChild(renderComment(reply, depth + 1, accessToken));
    });
    
    div.appendChild(repliesDiv);
  }
  
  return div;
}

// Load and display comments
async function loadComments(postId, accessToken) {
  const headers = {};
  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }
  
  const response = await fetch(
    `http://localhost:8000/api/v1/communities/posts/${postId}/comments`,
    { headers }
  );
  
  if (response.ok) {
    const data = await response.json();
    const container = document.getElementById('comments-container');
    container.innerHTML = '';
    
    // Update header
    document.getElementById('comment-count').textContent = 
      `Comments (${data.total})`;
    
    if (data.total_with_replies > data.total) {
      document.getElementById('reply-count').textContent = 
        ` · ${data.total_with_replies - data.total} replies`;
    }
    
    // Render comments
    data.comments.forEach(comment => {
      container.appendChild(renderComment(comment, 0, accessToken));
    });
  }
}
```

---

## Database Setup

### Create comment_likes Table

Run this script to create the necessary table:

```bash
python scripts/create_comment_likes_table.py
```

Or manually:

```sql
CREATE TABLE comment_likes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    comment_id UUID NOT NULL REFERENCES post_comments(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(comment_id, user_id)
);

CREATE INDEX idx_comment_likes_comment_id ON comment_likes(comment_id);
CREATE INDEX idx_comment_likes_user_id ON comment_likes(user_id);
```

---

## Summary

### Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/posts/{id}/comments` | GET | Optional | Get nested comments with like status |
| `/posts/{id}/comments` | POST | Required | Create comment or reply |
| `/comments/{id}/like` | POST | Required | Like a comment |
| `/comments/{id}/like` | DELETE | Required | Unlike a comment |

### Key Features

✅ **Nested structure** - Replies organized hierarchically  
✅ **User info** - Username and avatar included  
✅ **Like system** - Like/unlike with count tracking  
✅ **Like status** - Shows if user has liked  
✅ **Efficient queries** - Single query for all comments  
✅ **Pagination** - Applied to top-level comments only  
✅ **Optional auth** - Works for guests, enhanced for users  

### Response Structure

```
Top-level comment 1
├── Reply 1.1
│   └── Reply 1.1.1
└── Reply 1.2
Top-level comment 2
└── Reply 2.1
```

This structure makes it easy for the frontend to render threaded conversations!
