document.addEventListener('DOMContentLoaded', function() {
    const likeForms = document.querySelectorAll('.like-form');
    
    likeForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const url = this.getAttribute('action');
            const postId = url.match(/\/(?:like|unlike)\/(\d+)/)[1]; 
            
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
                
                if (data.liked) {
                    button.classList.add('liked');
                    button.innerHTML = '<i class="fas fa-heart"></i> Unlike';
                    this.action = `/unlike/${postId}?next=${encodeURIComponent(window.location.pathname)}`;
                } else {
                    button.classList.remove('liked');
                    button.innerHTML = '<i class="far fa-heart"></i> Like';
                    this.action = `/like/${postId}?next=${encodeURIComponent(window.location.pathname)}`;
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

