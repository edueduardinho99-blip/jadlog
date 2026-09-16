// Variáveis para controlar o slider
let currentIndex = 0;
const slides = document.querySelectorAll('.banner-slide');
const totalSlides = slides.length;
let slideInterval;

// Função para mover para o próximo slide
function moveToNextSlide() {
    currentIndex = (currentIndex + 1) % totalSlides;
    updateSlidePosition();
}

// Função para mover para o slide anterior
function moveToPrevSlide() {
    currentIndex = (currentIndex - 1 + totalSlides) % totalSlides;
    updateSlidePosition();
}

// Função para atualizar a posição do slide
function updateSlidePosition() {
    document.querySelector('.banner-wrapper').style.transform = `translateX(-${currentIndex * 100}%)`;
}

// Função para iniciar o carrossel automático
function startSlideShow() {
    // Limpa qualquer intervalo existente antes de criar um novo
    if (slideInterval) {
        clearInterval(slideInterval);
    }
    slideInterval = setInterval(moveToNextSlide, 3000);
}

// Função para pausar o carrossel
function pauseSlideShow() {
    clearInterval(slideInterval);
}

// Iniciar o carrossel assim que a página carregar
document.addEventListener('DOMContentLoaded', () => {
    // Verifica se existem slides
    if (totalSlides > 0) {
        // Inicializa os indicadores de navegação (caso existam)
        updateSlidePosition();
        
        // Inicia o slideshow automático
        startSlideShow();
        
        // Opcional: pausar o slideshow quando o mouse estiver sobre o banner
        const bannerContainer = document.querySelector('.banner-container');
        if (bannerContainer) {
            bannerContainer.addEventListener('mouseenter', pauseSlideShow);
            bannerContainer.addEventListener('mouseleave', startSlideShow);
        }
    }
});
