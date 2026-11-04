/* FT-53 to FT-56: Render the selected month's category expense chart. */
(() => {
  const canvas = document.getElementById("category-spending-chart");
  const labelsNode = document.getElementById("category-chart-labels");
  const valuesNode = document.getElementById("category-chart-values");
  if (!canvas || !labelsNode || !valuesNode || typeof Chart === "undefined") return;

  const labels = JSON.parse(labelsNode.textContent);
  const values = JSON.parse(valuesNode.textContent).map(Number);
  if (!labels.length || labels.length !== values.length || values.some((value) => !Number.isFinite(value))) return;

  const colors = ["#1d4ed8", "#15803d", "#b45309", "#7c3aed", "#0f766e", "#be123c", "#475569", "#a16207"];
  const formatMoney = (amount) => `$${amount.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  new Chart(canvas, {
    type: "doughnut",
    data: {
      labels,
      datasets: [{
        label: "Expenses",
        data: values,
        backgroundColor: labels.map((_, index) => colors[index % colors.length]),
        borderColor: "#ffffff",
        borderWidth: 3,
        hoverOffset: 5,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "62%",
      plugins: {
        legend: { position: "bottom", labels: { usePointStyle: true, padding: 18 } },
        tooltip: { callbacks: { label: (context) => `${context.label}: ${formatMoney(context.parsed)}` } },
      },
    },
  });
})();
