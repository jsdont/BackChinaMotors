document.addEventListener('DOMContentLoaded', function () {
  var textarea = document.getElementById('id_images');
  if (!textarea) return;

  var preview = document.createElement('div');
  preview.style.display = 'flex';
  preview.style.flexWrap = 'wrap';
  preview.style.gap = '8px';
  preview.style.marginTop = '8px';
  textarea.parentNode.insertBefore(preview, textarea.nextSibling);

  function renderPreview() {
    var urls = textarea.value.split('\n').map(function (s) { return s.trim(); }).filter(Boolean);
    preview.innerHTML = '';
    urls.forEach(function (url) {
      var img = document.createElement('img');
      img.src = url;
      img.title = url;
      img.style.width = '100px';
      img.style.height = '70px';
      img.style.objectFit = 'cover';
      img.style.borderRadius = '6px';
      img.style.border = '1px solid #ccc';
      img.onerror = function () {
        img.style.opacity = '0.3';
        img.title = 'Не удалось загрузить: ' + url;
      };
      preview.appendChild(img);
    });
  }

  textarea.addEventListener('input', renderPreview);
  renderPreview();
});
