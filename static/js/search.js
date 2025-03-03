document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('userSearchInput');
    const searchResults = document.getElementById('searchResults');
    const clearSearchBtn = document.getElementById('clearSearchBtn');
    let searchTimeout = null;

    searchInput.addEventListener('input', function() {
        if (this.value.length > 0) {
            clearSearchBtn.style.display = 'block';
        } else {
            clearSearchBtn.style.display = 'none';
            fetchAllUsers(); 
        }
        
        clearTimeout(searchTimeout);
        if (this.value.length > 0) {
            searchTimeout = setTimeout(function() {
                searchUsers(searchInput.value);
            }, 300);
        }
    });

    clearSearchBtn.addEventListener('click', function() {
        searchInput.value = '';
        clearSearchBtn.style.display = 'none';
        fetchAllUsers();
        searchInput.focus();
    });

    function searchUsers(query) {
        searchResults.innerHTML = '<div class="search-loading"><i class="fas fa-spinner fa-spin"></i> Searching...</div>';
        
        fetch('/search_users?q=' + encodeURIComponent(query), {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            renderUsers(data.users);
        })
        .catch(error => {
            console.error('Error:', error);
            searchResults.innerHTML = '<div class="search-no-results">An error occurred while searching.</div>';
        });
    }

    function fetchAllUsers() {
        fetch('/users', {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            renderUsers(data.users);
        })
        .catch(error => {
            console.error('Error:', error);
            searchResults.innerHTML = '<div class="search-no-results">An error occurred while fetching users.</div>';
        });
    }
    
    function renderUsers(users) {
        if (users.length === 0) {
            searchResults.innerHTML = '<div class="search-no-results"><i class="fas fa-search"></i> No users found.</div>';
            return;
        }
        
        let html = '<div class="users-grid">';
        
        users.forEach(user => {
            html += `
                <div class="user-card">
                    <div class="user-avatar">
                        <img src="https://ui-avatars.com/api/?name=${user.username}&background=random" alt="Avatar">
                    </div>
                    <div class="user-info">
                        <h3><a href="/profile/${user.username}">${user.username}</a></h3>
                        <p class="join-date">Member since ${user.join_date}</p>
                    </div>
                    <div class="user-actions">
                        ${user.is_friend ? 
                            `<a href="/remove_friend/${user.id}" class="btn btn-danger">Unfollow</a>` : 
                            `<a href="/add_friend/${user.id}" class="btn btn-primary">Follow</a>`
                        }
                    </div>
                </div>
            `;
        });
        
        html += '</div>';
        searchResults.innerHTML = html;
    }
});