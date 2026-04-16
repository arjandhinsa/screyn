import { NavLink, Route, Routes } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import History from './pages/History'
import Settings from './pages/Settings'
import './App.css'

export default function App() {
  return (
    <div className="app">
      <div className="grid-bg" />
      <div className="content">
        <header className="app-header">
          <div className="brand">
            <div className="brand-logo mono">SCREYN</div>
            <div className="brand-tagline">screen health optimiser</div>
          </div>
          <nav className="app-nav">
            <NavLink to="/" end className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>Dashboard</NavLink>
            <NavLink to="/history" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>History</NavLink>
            <NavLink to="/settings" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>Settings</NavLink>
          </nav>
        </header>

        <main>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/history" element={<History />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>

        <footer className="app-footer">
          <span className="mono">SEYN</span>
          <span>· part of the ecosystem</span>
        </footer>
      </div>
    </div>
  )
}
