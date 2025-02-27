import json
import logging
import sqlite3
import aiosqlite
from datetime import datetime
from typing import Optional, List, Dict, Any, Union

def analyze_emotion(text):
    """
    Analyze the emotional content of text using simple keyword matching.
    Returns Discord-compatible emoji
    """
    # Define emotion keywords and corresponding Discord emojis
    emotions = {
        'joy': (['happy', 'joy', 'excited', 'great', 'wonderful', 'love', 'glad', 'yay', 'woohoo', 'hehe', 'haha'], '😄'),
        'sadness': (['sad', 'sorry', 'unfortunate', 'regret', 'miss', 'lonely', 'sigh', 'alas', 'ugh'], '😢'),
        'anger': (['angry', 'mad', 'furious', 'annoyed', 'frustrated', 'grr', 'ugh', 'argh'], '😠'),
        'fear': (['afraid', 'scared', 'worried', 'nervous', 'anxious', 'eek', 'yikes'], '😨'),
        'surprise': (['wow', 'amazing', 'incredible', 'unexpected', 'surprised', 'whoa', 'woah', 'omg', 'oh my'], '😮'),
        'neutral': (['ok', 'fine', 'alright', 'neutral', 'hmm', 'mhm'], '👍'),
        'expressive': (['*', 'moans', 'sighs', 'gasps', 'squeals', 'giggles', 'laughs', 'cries', 'screams'], '🎭')
    }
    
    # Convert text to lowercase for matching
    text = text.lower()
    
    # First check for expressive actions (usually in asterisks or explicit actions)
    if any(action in text for action in emotions['expressive'][0]):
        return emotions['expressive'][1]
    
    # Count emotion keywords
    emotion_counts = {emotion: 0 for emotion in emotions if emotion != 'expressive'}
    for emotion, (keywords, _) in emotions.items():
        if emotion != 'expressive':  # Skip expressive since we handled it above
            for keyword in keywords:
                emotion_counts[emotion] += text.count(keyword)
    
    # Find emotion with highest count
    max_emotion = max(emotion_counts.items(), key=lambda x: x[1])
    
    # Return corresponding emoji, default to neutral
    return emotions[max_emotion[0]][1] if max_emotion[1] > 0 else emotions['neutral'][1]

async def get_message_history(channel_id: str, limit: int = 50) -> List[Dict]:
    """
    Fetch the last N messages from the database for a given channel
    Returns list of messages in API format (role, content)
    """
    try:
        db_path = 'databases/interaction_logs.db'
        async with aiosqlite.connect(db_path) as conn:
            cursor = await conn.cursor()
            
            # Get last N messages ordered by timestamp
            await cursor.execute("""
                SELECT content, is_assistant, persona_name, timestamp
                FROM messages 
                WHERE channel_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (str(channel_id), limit))
            
            rows = await cursor.fetchall()
            messages = []
            seen_content = set()
            
            for content, is_assistant, persona_name, timestamp in rows:
                # Skip if we've seen this exact content before
                if content in seen_content:
                    continue
                seen_content.add(content)
                
                # For assistant messages
                if is_assistant:
                    # Remove model name prefix if present
                    if content.startswith('[') and ']' in content:
                        content = content[content.index(']')+1:].strip()
                    
                    # Add name field for vision messages
                    if persona_name == "Llama-Vision":
                        messages.append({
                            "role": "assistant",
                            "name": persona_name,
                            "content": content
                        })
                    else:
                        messages.append({
                            "role": "assistant",
                            "content": content
                        })
                else:
                    messages.append({
                        "role": "user",
                        "content": content
                    })
            
            # Reverse to get chronological order
            messages.reverse()
            return messages

    except Exception as e:
        logging.error(f"Failed to fetch message history: {str(e)}")
        return []

async def store_alt_text(message_id: str, channel_id: str, alt_text: str, attachment_url: str) -> bool:
    """Store image alt text in the database"""
    try:
        db_path = 'databases/interaction_logs.db'
        async with aiosqlite.connect(db_path) as conn:
            await conn.execute("""
                INSERT INTO image_alt_text (message_id, channel_id, alt_text, attachment_url)
                VALUES (?, ?, ?, ?)
            """, (str(message_id), str(channel_id), alt_text, attachment_url))
            await conn.commit()
            logging.debug(f"Stored alt text for message {message_id}")
            return True
    except Exception as e:
        logging.error(f"Failed to store alt text: {str(e)}")
        return False

async def get_alt_text(message_id: str) -> Optional[str]:
    """Retrieve alt text for a message"""
    try:
        db_path = 'databases/interaction_logs.db'
        async with aiosqlite.connect(db_path) as conn:
            cursor = await conn.cursor()
            await cursor.execute("""
                SELECT alt_text FROM image_alt_text
                WHERE message_id = ?
            """, (str(message_id),))
            result = await cursor.fetchone()
            return result[0] if result else None
    except Exception as e:
        logging.error(f"Failed to get alt text: {str(e)}")
        return None

async def get_unprocessed_images(channel_id: str, limit: int = 50) -> List[Dict]:
    """Get messages with images that don't have alt text"""
    try:
        db_path = 'databases/interaction_logs.db'
        async with aiosqlite.connect(db_path) as conn:
            cursor = await conn.cursor()
            await cursor.execute("""
                SELECT m.id, m.channel_id, m.content
                FROM messages m
                LEFT JOIN image_alt_text i ON m.id = i.message_id
                WHERE m.channel_id = ?
                AND m.content LIKE '%https://%'
                AND i.message_id IS NULL
                ORDER BY m.timestamp DESC
                LIMIT ?
            """, (str(channel_id), limit))
            rows = await cursor.fetchall()
            return [{"message_id": row[0], "channel_id": row[1], "content": row[2]} 
                   for row in rows]
    except Exception as e:
        logging.error(f"Failed to get unprocessed images: {str(e)}")
        return []

async def log_interaction(user_id: Union[int, str], guild_id: Optional[Union[int, str]], 
                        persona_name: str, user_message: Union[str, Dict, Any], assistant_reply: str, 
                        emotion: Optional[str] = None, channel_id: Optional[Union[int, str]] = None):
    """
    Log interaction details to SQLite database
    """
    try:
        db_path = 'databases/interaction_logs.db'
        async with aiosqlite.connect(db_path) as conn:
            # Convert all values to strings to prevent type issues
            channel_id = str(channel_id) if channel_id else None
            guild_id = str(guild_id) if guild_id else None
            user_id = str(user_id)
            persona_name = str(persona_name)
            
            # Handle user_message that might be a Discord Message object or other complex type
            if isinstance(user_message, str):
                user_message_content = user_message
            elif isinstance(user_message, dict):
                user_message_content = json.dumps(user_message)
            else:
                # Try to convert to string, fallback to repr if needed
                try:
                    user_message_content = str(user_message)
                except:
                    user_message_content = repr(user_message)
            
            assistant_reply = str(assistant_reply)
            emotion = str(emotion) if emotion else None
            timestamp = datetime.now().isoformat()
            
            # Log user message
            cursor = await conn.cursor()
            await cursor.execute("""
                INSERT INTO messages (
                    channel_id, guild_id, user_id, content, 
                    is_assistant, emotion, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (channel_id, guild_id, user_id, user_message_content, False, None, timestamp))
            
            user_message_id = cursor.lastrowid
            
            # Log assistant reply
            await cursor.execute("""
                INSERT INTO messages (
                    channel_id, guild_id, user_id, persona_name,
                    content, is_assistant, emotion, parent_message_id,
                    timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (channel_id, guild_id, user_id, persona_name,
                 assistant_reply, True, emotion, user_message_id, timestamp))
            
            await conn.commit()
            logging.debug(f"Successfully logged interaction for user {user_id}")
            
    except Exception as e:
        logging.error(f"Failed to log interaction: {str(e)}")
        # Fallback to JSONL logging if database fails
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'user_id': str(user_id),
                'guild_id': str(guild_id) if guild_id else None,
                'channel_id': str(channel_id) if channel_id else None,
                'persona': str(persona_name),
                'user_message': str(user_message_content) if 'user_message_content' in locals() else str(user_message),
                'assistant_reply': str(assistant_reply),
                'emotion': str(emotion) if emotion else None
            }
            
            with open('interaction_logs.jsonl', 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')
                
        except Exception as e2:
            logging.error(f"Failed to log interaction to JSONL: {str(e2)}")
