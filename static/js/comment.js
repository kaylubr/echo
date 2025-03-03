function openDeleteModal() {
    document.getElementById('deletePostModal').style.display = 'block';
}

function closeDeleteModal() {
    document.getElementById('deletePostModal').style.display = 'none';
}

function openCommentDeleteModal(commentId) {
    document.getElementById('deleteCommentForm').action = `/comment/${commentId}/delete`;
    document.getElementById('deleteCommentModal').style.display = 'block';
}

function closeCommentDeleteModal() {
    document.getElementById('deleteCommentModal').style.display = 'none';
}