export default function StatCard({ icon: Icon, label, value, detail, tone = "" }) {
  return (
    <div className="stat-card">
      <div className={`stat-icon ${tone}`}><Icon size={21} /></div>
      <div>
        <p>{label}</p>
        <h3>{value}</h3>
        <small>{detail}</small>
      </div>
    </div>
  );
}
