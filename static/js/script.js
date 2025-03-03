document.addEventListener('DOMContentLoaded', function() {
    const likeForms = document.querySelectorAll('.like-form');
    
    likeForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const url = this.getAttribute('action');
            
            fetch(url, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('likes-count').textContent = data.likes_count;
                
                const button = this.querySelector('button');
                const icon = button.querySelector('i');
                
                if (data.liked) {
                    button.classList.add('liked');
                    icon.className = 'fas fa-heart';
                    button.textContent = ' Unlike';
                    button.prepend(icon);
                    this.action = "{{ url_for('unlike_post', post_id=post.id, next=request.path) }}";
                } else {
                    button.classList.remove('liked');
                    icon.className = 'far fa-heart';
                    button.textContent = ' Like';
                    button.prepend(icon);
                    this.action = "{{ url_for('like_post', post_id=post.id, next=request.path) }}";
                }
            })
            .catch(error => console.error('Error:', error));
        });
    });
});

function openDeleteModal() {
    document.getElementById('deletePostModal').style.display = 'flex';
}

function closeDeleteModal() {
    document.getElementById('deletePostModal').style.display = 'none';
}

window.onclick = function(event) {
    const modal = document.getElementById('deletePostModal');
    if (event.target === modal) {
        closeDeleteModal();
    }
};

document.addEventListener('keydown', function(event) {
    if (event.key === "Escape") {
        closeDeleteModal();
    }
});