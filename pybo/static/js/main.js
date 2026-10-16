// ==========================================================================
// 1. 지역별 / 테마별 탭 버튼 및 드롭다운 전환 제어
// ==========================================================================
const tabButtons = document.querySelectorAll('.tab-btn, [data-tab]');
const tabContents = document.querySelectorAll('.travel-tab-content');

tabButtons.forEach(function (button) {
    button.addEventListener('click', function (e) {
        e.preventDefault();

        const target = button.dataset.tab;
        if (!target) return;

        tabButtons.forEach(function (btn) {
            btn.classList.remove('active');
        });
        button.classList.add('active');

        tabContents.forEach(function (content) {
            content.classList.remove('active');
            content.style.display = "none";
        });

        const targetContent = document.getElementById(target + '-tab');
        if (targetContent) {
            targetContent.classList.add('active');
            targetContent.style.display = "block";
        }
    });
});

const travelDropdown = document.querySelector('.nav-item.dropdown, .dropdown');
const dropdownMenu = document.querySelector('.dropdown-menu, .travel-tab-content-wrapper');

let dropdownTimeoutId;

if (travelDropdown && dropdownMenu) {
    travelDropdown.addEventListener('mouseenter', function () {
        clearTimeout(dropdownTimeoutId);
        dropdownMenu.classList.add('show');
        travelDropdown.classList.add('show');
    });

    travelDropdown.addEventListener('mouseleave', function () {
        dropdownTimeoutId = setTimeout(function () {
            dropdownMenu.classList.remove('show');
            travelDropdown.classList.remove('show');
        }, 500);
    });
}

// ==========================================================================
// 2. M타임딜 1초 주기 실시간 카운트다운 타이머 엔진
// ==========================================================================
function updateMTimeDeals() {
    const timerElements = document.querySelectorAll('.time-text, .sub-timer, [data-endtime]');

    timerElements.forEach(function (el) {
        const endTimeStr = el.getAttribute('data-endtime');
        if (!endTimeStr) return;

        const endTime = new Date(endTimeStr).getTime();
        const now = new Date().getTime();
        const distance = endTime - now;

        if (distance <= 0) {
            el.innerText = "🚨 핫딜 판매가 마감되었습니다.";
            el.style.color = "#999";
            return;
        }

        const days = Math.floor(distance / (1000 * 60 * 60 * 24));
        const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((distance % (1000 * 60)) / 1000);

        el.innerHTML = `<strong>${days}</strong>일 <strong>${String(hours).padStart(2, '0')}</strong>:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')} 남았습니다.`;
    });
}

updateMTimeDeals();
setInterval(updateMTimeDeals, 1000);

// ==========================================================================
// 3. 후기 더보기 / 접기 토글
// ==========================================================================
document.addEventListener("DOMContentLoaded", function () {
    const btnMore = document.getElementById("btnMoreReviews");
    const reviewGrid = document.querySelector(".review-grid");

    if (btnMore && reviewGrid) {
        btnMore.addEventListener("click", function () {
            reviewGrid.classList.toggle("is-active");

            if (reviewGrid.classList.contains("is-active")) {
                btnMore.textContent = "후기 접기 △";
            } else {
                btnMore.textContent = "후기 더보기 ▽";
                reviewGrid.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        });
    }
});