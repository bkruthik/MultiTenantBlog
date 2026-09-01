from django.db import models
from django.contrib.auth.models import User


def auto_detect_category(name, description=""):
    """
    Intelligently infer the community category from title/name and description keywords.
    """
    text = f"{name} {description}".lower()
    if any(k in text for k in ['code', 'dev', 'python', 'react', 'javascript', 'django', 'ai', 'ml', 'tech', 'software', 'api', 'database', 'css', 'html', 'cloud', 'cyber', 'data', 'algorithm', 'web', 'program', 'linux', 'backend', 'frontend']):
        return 'Technology & Coding'
    if any(k in text for k in ['study', 'exam', 'math', 'learn', 'college', 'school', 'notes', 'science', 'history', 'physics', 'course', 'quiz', 'academic', 'book', 'university']):
        return 'Study & Education'
    if any(k in text for k in ['sport', 'football', 'cricket', 'fitness', 'gym', 'workout', 'run', 'athlete', 'league', 'match', 'basketball', 'tennis', 'soccer', 'training', 'marathon']):
        return 'Sports & Fitness'
    if any(k in text for k in ['meme', 'joke', 'funny', 'humor', 'lol', 'fun', 'laugh', 'comedy', 'humour']):
        return 'Humor & Memes'
    if any(k in text for k in ['game', 'gaming', 'esports', 'playstation', 'xbox', 'steam', 'rpg', 'fps']):
        return 'Gaming'
    if any(k in text for k in ['music', 'song', 'audio', 'band', 'guitar', 'piano', 'hiphop', 'rock']):
        return 'Music & Audio'
    if any(k in text for k in ['art', 'design', 'photo', 'drawing', 'ui', 'ux', 'paint', 'creative']):
        return 'Art & Design'
    return 'General Community'


class Tenant(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True, default='')
    category = models.CharField(max_length=100, default='General Community')
    is_private = models.BooleanField(default=False)

    # Avatar: either an emoji OR an image URL
    avatar_emoji = models.CharField(max_length=10, blank=True, default='')
    avatar_url = models.URLField(max_length=500, blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def display_avatar(self):
        return self.avatar_emoji if self.avatar_emoji else self.name[0].upper()

    @property
    def has_image_avatar(self):
        return bool(self.avatar_url)


class ChatMessage(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='chat_messages')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.author.username} in {self.tenant.name}: {self.message[:30]}"
