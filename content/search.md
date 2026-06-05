---
title: "Search"
layout: "search"
---

<link href="/pagefind/pagefind-ui.css" rel="stylesheet">
<div id="search"></div>

<script src="/pagefind/pagefind-ui.js"></script>
<script>
  window.addEventListener('DOMContentLoaded', () => {
    new PagefindUI({
      element: "#search",
      showSubResults: true,
      showImages: false,
      excerptLength: 20,
      resetStyles: false,
    });
  });
</script>