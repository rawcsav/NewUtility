document.querySelectorAll('.cloud-btn').forEach((button) => {
  button.addEventListener('mouseover', function () {
    this.parentElement.classList.add('hovered');
  });
  button.addEventListener('mouseout', function () {
    this.parentElement.classList.remove('hovered');
  });
});
