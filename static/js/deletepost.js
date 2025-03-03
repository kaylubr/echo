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