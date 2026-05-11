const gallery = document.getElementById('gallery');
const refreshBtn = document.getElementById('refresh-btn');
const themeBtn = document.getElementById('theme-toggle');
const searchInput = document.getElementById('search-input');
const searchBtn = document.getElementById('search-btn');

async function loadRandomPhotos() {
    gallery.innerHTML = '<p style="text-align:center; padding:20px;">⏳ جاري تحميل الصور...</p>';
    
    try {
        const response = await fetch('/photos');
        const photos = await response.json();
        displayPhotos(photos);
    } catch (error) {
        gallery.innerHTML = '<p style="text-align:center; color:red; padding:20px;">❌ فشل في تحميل الصور</p>';
    }
}

async function searchPhotos() {
    const query = searchInput.value.trim();
    
    if (!query) {
        alert('الرجاء ادخال كلمة للبحث');
        return;
    }
    
    gallery.innerHTML = '<p style="text-align:center; padding:20px;">🔍 جاري البحث عن: ' + query + '</p>';
    
    try {
        const response = await fetch('/search?q=' + encodeURIComponent(query));
        const photos = await response.json();
        
        if (photos.length === 0) {
            gallery.innerHTML = '<p style="text-align:center; padding:20px;">😕 لا توجد نتائج لـ: ' + query + '</p>';
        } else {
            displayPhotos(photos);
        }
    } catch (error) {
        gallery.innerHTML = '<p style="text-align:center; color:red; padding:20px;">❌ فشل في البحث</p>';
    }
}

function displayPhotos(photos) {
    gallery.innerHTML = '';
    
    photos.forEach(function(photo) {
        const card = document.createElement('div');
        card.className = 'card';
        
        const img = document.createElement('img');
        img.src = photo.url;
        img.loading = 'lazy';
        img.alt = photo.title || 'صورة';
        img.onerror = function() {
            this.src = 'https://via.placeholder.com/400x500/e60023/ffffff?text=صورة';
        };
        
        card.appendChild(img);
        gallery.appendChild(card);
    });
}

// زر التحديث
if (refreshBtn) {
    refreshBtn.addEventListener('click', loadRandomPhotos);
}

// زر البحث
if (searchBtn) {
    searchBtn.addEventListener('click', searchPhotos);
}

// زر Enter للبحث
if (searchInput) {
    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            searchPhotos();
        }
    });
}

// زر تغيير الثيم
if (themeBtn) {
    const savedTheme = localStorage.getItem('theme');
    
    if (savedTheme === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
        themeBtn.innerText = '☀️';
    }
    
    themeBtn.addEventListener('click', function() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        
        if (currentTheme === 'dark') {
            document.documentElement.removeAttribute('data-theme');
            themeBtn.innerText = '🌙';
            localStorage.setItem('theme', 'light');
        } else {
            document.documentElement.setAttribute('data-theme', 'dark');
            themeBtn.innerText = '☀️';
            localStorage.setItem('theme', 'dark');
        }
    });
}

// تحميل اولي
window.addEventListener('DOMContentLoaded', loadRandomPhotos);