// 최근 문장 추가 예시
const recentList = document.getElementById('recent-list');
function addRecentSentence(sentence) {
  const li = document.createElement('li');
  li.textContent = sentence;
  recentList.prepend(li);
  while (recentList.children.length > 5) {
    recentList.removeChild(recentList.lastChild);
  }
}
// 정지 버튼 눌렀을 때 로딩 화면
const playBtn = document.getElementById('play-btn');
const stopBtn = document.getElementById('stop-btn');
const voiceMain = document.getElementById('voice-main');
const analysisProgress = document.getElementById('analysis-progress');

function resetButtons() {
  playBtn.style.backgroundColor = '#fff';
  stopBtn.style.backgroundColor = '#fff';
}

stopBtn.addEventListener('click', () => {
  resetButtons();
  stopBtn.style.backgroundColor = '#f8d7da';
  voiceMain.style.display = 'none';
  analysisProgress.style.display = 'flex';
});

voiceMain.style.display = 'none';
analysisProgress.style.display = 'flex';


// 메뉴 버튼 클릭 시 알림
/*
document.querySelectorAll('.menu-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    alert(`${btn.textContent} 기능은 준비 중입니다.`);
  });
});

// 개발 중에는 서비스워커 등록 코드를 주석 처리하세요

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js')
      .then(registration => {
        console.log('ServiceWorker 등록 성공:', registration.scope);
      })
      .catch(error => {
        console.log('ServiceWorker 등록 실패:', error);
      });
  });
}
*/

