function openDeleteModal() {
    document.getElementById('deletePostModal').style.display = 'block';
}

function closeDeleteModal() {
    document.getElementById('deletePostModal').style.display = 'none';
}

function openCommentDeleteModal(commentId) {
    document.getElementById('deleteCommentForm').action = "{{ url_for('delete_comment', comment_id=0) }}".replace('/0', '/' + commentId);
    document.getElementById('deleteCommentModal').style.display = 'block';
}

function closeCommentDeleteModal() {
    document.getElementById('deleteCommentModal').style.display = 'none';
}