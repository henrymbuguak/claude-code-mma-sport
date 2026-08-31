document.querySelectorAll("time[data-utc]").forEach((el) => {
  const date = new Date(el.dataset.utc);
  if (Number.isNaN(date.getTime())) {
    return;
  }
  el.textContent = new Intl.DateTimeFormat(undefined, {
    weekday: "short",
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  }).format(date);
});
