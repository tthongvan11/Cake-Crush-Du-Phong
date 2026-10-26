// Giữ menu thao tác nổi bên cạnh nút ba chấm mà không thay đổi kích thước bảng.
const rowActions = [...document.querySelectorAll('.hr-row-actions')]; // Dùng chung cho nhân viên và hợp đồng.

function closeRowMenus(except = null) { // Có thể giữ lại menu vừa mở.
    rowActions.forEach((actions) => { // Duyệt các nút thao tác trong trang hiện tại.
        if (actions !== except) actions.open = false; // Đóng menu khác bằng cơ chế details có sẵn.
    }); // Không thay đổi nội dung hoặc chiều rộng bảng.
} // Kết thúc hàm đóng menu.

rowActions.forEach((actions) => { // Cài đặt hành vi cho từng dòng.
    actions.addEventListener('toggle', () => { // Cả chuột và bàn phím đều kích hoạt được.
        if (!actions.open) return; // Menu đóng không cần tính vị trí.
        closeRowMenus(actions); // Chỉ mở một menu tại một thời điểm.
        const button = actions.querySelector('summary').getBoundingClientRect(); // Vị trí nút theo màn hình.
        const menu = actions.querySelector('.hr-row-menu'); // Menu tương ứng với đúng dòng.
        const { width, height } = menu.getBoundingClientRect(); // Đo kích thước menu đang mở.
        const left = Math.max(8, Math.min(button.right - width, window.innerWidth - width - 8)); // Giữ menu trong mép ngang màn hình.
        const top = button.bottom + height + 6 <= window.innerHeight - 8 // Kiểm tra khoảng trống bên dưới.
            ? button.bottom + 6 // Mở xuống dưới khi còn đủ chỗ.
            : Math.max(8, button.top - height - 6); // Mở lên trên khi nút nằm gần cuối màn hình.
        menu.style.left = `${left}px`; // Đặt tọa độ ngang, không tham gia tính chiều rộng cột.
        menu.style.top = `${top}px`; // Đặt tọa độ dọc bên cạnh nút.
    }); // Kết thúc xử lý mở menu.
}); // Kết thúc cài đặt các dòng.

document.addEventListener('click', (event) => { // Đóng menu khi bấm ra ngoài.
    if (!event.target.closest('.hr-row-actions')) closeRowMenus(); // Bấm vào liên kết trong menu vẫn hoạt động bình thường.
}); // Kết thúc xử lý chuột.
document.addEventListener('keydown', (event) => { // Hỗ trợ đóng menu bằng bàn phím.
    if (event.key !== 'Escape') return; // Phím khác giữ nguyên hành vi mặc định.
    const opened = rowActions.find((actions) => actions.open); // Tìm menu đang mở.
    closeRowMenus(); // Escape đóng menu hiện tại.
    if (opened) opened.querySelector('summary').focus(); // Trả vị trí chọn về nút ba chấm.
}); // Kết thúc xử lý bàn phím.
document.addEventListener('scroll', () => closeRowMenus(), true); // Cuộn bảng hoặc trang thì đóng để menu không lệch dòng.
window.addEventListener('resize', () => closeRowMenus()); // Đóng khi kích thước màn hình thay đổi.
