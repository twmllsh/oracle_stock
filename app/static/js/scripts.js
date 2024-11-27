function showInfo(item_code) {
    fetch(`/kor/api/?item_code=${item_code}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            const infoPanel = document.getElementById('infoPanel');
            infoPanel.innerHTML = `
                <h5>${data.item_code} 정보</h5>
                <p><strong>message:</strong> ${data.message}</p>
                <p>${data.status}</p>
            `;
            const graphContainer = document.getElementById('graph-container'); 
            graphContainer.innerHTML = data.graph_html;  // 백틱 사용하지 않음, 안전성 확인 필요
        })
        .catch(error => {
            const infoPanel = document.getElementById('infoPanel');
            infoPanel.innerHTML = `<p>주식 정보를 찾을 수 없습니다.</p>`;
            console.error('Error fetching data:', error);  // 에러 로그 추가
        });
}
