from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Category, Post, Comment
import markdown
import re

def render_content(raw):
    """将 Markdown + LaTeX 渲染成 HTML，保护 LaTeX 块不被 Markdown 解析器破坏"""
    math_blocks = {}
    counter = [0]

    def protect(m):
        key = f'MATHBLOCK{counter[0]}ENDMATH'
        math_blocks[key] = m.group(0)
        counter[0] += 1
        return key

    raw = re.sub(r'\$\$.+?\$\$', protect, raw, flags=re.DOTALL)
    raw = re.sub(r'\$[^\$\n]+?\$', protect, raw)

    md = markdown.Markdown(extensions=['fenced_code', 'tables', 'nl2br', 'toc'])
    html = md.convert(raw)

    for key, val in math_blocks.items():
        html = html.replace(key, val)

    return html

def index(request):
    categories = Category.objects.all()
    post_list = Post.objects.order_by('-created_at')
    paginator = Paginator(post_list, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'forum/index.html', {'categories': categories, 'posts': page})

def search(request):
    query = request.GET.get('q', '').strip()
    categories = Category.objects.all()
    results = Post.objects.none()
    if query:
        results = Post.objects.filter(
            Q(title__icontains=query) | Q(content__icontains=query)
        ).order_by('-created_at')
    paginator = Paginator(results, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'forum/search.html', {
        'posts': page, 'query': query,
        'categories': categories,
        'count': results.count() if query else 0
    })

def category(request, pk):
    cat = get_object_or_404(Category, pk=pk)
    posts = cat.posts.order_by('-created_at')
    all_categories = Category.objects.all()
    return render(request, 'forum/category.html', {'category': cat, 'posts': posts, 'all_categories': all_categories})

def post_detail(request, pk):
    post = get_object_or_404(Post, pk=pk)
    post.views += 1
    post.save(update_fields=['views'])
    comments = post.comments.order_by('created_at')

    # 优先读取 md 文件内容
    if post.md_file:
        try:
            with open(post.md_file.path, 'r', encoding='utf-8') as f:
                raw = f.read()
        except Exception:
            raw = post.content
    else:
        raw = post.content

    rendered_content = render_content(raw)

    if request.method == 'POST':
        content = request.POST.get('content')
        author = request.POST.get('author', '匿名')
        if content:
            Comment.objects.create(post=post, content=content, author=author)
            return redirect('post_detail', pk=pk)

    return render(request, 'forum/post_detail.html', {
        'post': post, 'comments': comments, 'rendered_content': rendered_content
    })

def post_create(request):
    categories = Category.objects.all()
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content', '')
        author = request.POST.get('author', '匿名')
        category_id = request.POST.get('category')
        md_file = request.FILES.get('md_file')
        if title and category_id:
            post = Post.objects.create(
                title=title, content=content,
                author=author, category_id=category_id
            )
            if md_file:
                post.md_file = md_file
                post.save()
            return redirect('post_detail', pk=post.pk)
    return render(request, 'forum/post_create.html', {'categories': categories})
