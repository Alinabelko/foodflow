import React, { useState, useEffect } from 'react';
import { Calendar, Utensils, Clock } from 'lucide-react';
import { getData, approveMealPlan } from '../api';
import { translations as t } from '../translations';
import './Dashboard.css';

const MenuCard = ({ meal }) => (
    <div className="menu-card">
        <div className="meal-icon">
            <Utensils size={24} />
        </div>
        <div className="meal-content">
            <span className="meal-type">{meal.meal_type}</span>
            <h3>{meal.dish_name}</h3>
            {meal.notes && <p className="notes">{meal.notes}</p>}
        </div>
    </div>
);

const Dashboard = ({ language }) => {
    const [menu, setMenu] = useState({ confirmed: [], pending: {}, pendingDates: [] });
    const [loading, setLoading] = useState(true);
    const today = new Date().toISOString().split('T')[0];
    const text = t[language] || t.en;

    const handleApprove = async (dateToApprove) => {
        try {
            await approveMealPlan(dateToApprove);
            // Ideally we'd remove that date locally or reload
            window.location.reload();
        } catch (err) {
            console.error(err);
            alert("Failed to approve");
        }
    };

    useEffect(() => {
        const fetchMenu = async () => {
            try {
                const res = await getData('meal_plans.csv');
                const allPlans = res.data;

                // Pending: Show ALL pending plans (future and today)
                const pendingMeals = allPlans.filter(m => m.status === 'pending');

                // Confirmed: Show ONLY today's confirmed plans
                const confirmedMeals = allPlans.filter(m =>
                    (m.status === 'confirmed' || !m.status) && m.date === today
                );

                // Sort by meal type order
                const order = { 'breakfast': 1, 'lunch': 2, 'snack': 3, 'dinner': 4 };
                const sortMeals = (meals) => meals.sort((a, b) => (order[a.meal_type] || 99) - (order[b.meal_type] || 99));

                sortMeals(confirmedMeals);

                // Group pending by date
                const pendingByDate = pendingMeals.reduce((acc, meal) => {
                    if (!acc[meal.date]) acc[meal.date] = [];
                    acc[meal.date].push(meal);
                    return acc;
                }, {});

                // Sort pending dates
                const sortedPendingDates = Object.keys(pendingByDate).sort();

                setMenu({ confirmed: confirmedMeals, pending: pendingByDate, pendingDates: sortedPendingDates });
            } catch (err) {
                console.error("Failed to fetch menu", err);
            } finally {
                setLoading(false);
            }
        };
        fetchMenu();
    }, [today]);

    return (
        <div className="dashboard">
            <header className="dash-header">
                <h1>{text.todaysMenu}</h1>
                <div className="date-badge">
                    <Calendar size={18} />
                    <span>{today}</span>
                </div>
            </header>

            <div className="menu-grid">
                {loading ? (
                    <div className="loading">{text.loading}</div>
                ) : (menu.confirmed.length > 0 || menu.pendingDates.length > 0) ? (
                    <>
                        {menu.pendingDates.length > 0 && (
                            <div className="pending-section">
                                <div className="section-header">
                                    <h2>{text.proposedMenu}</h2>
                                    {/* Approve all pending for the first date available (simplified) or all? 
                                        Let's just approve the first date for now or we need a more complex UI.
                                        For MVP, let's approve the FIRST pending date.
                                    */}
                                    <button
                                        className="btn-primary"
                                        onClick={() => handleApprove(menu.pendingDates[0])}
                                    >
                                        {text.approve} ({menu.pendingDates[0]})
                                    </button>
                                </div>

                                {menu.pendingDates.map(date => (
                                    <div key={date} className="date-group">
                                        <h3 style={{ fontSize: '1rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>{date}</h3>
                                        {menu.pending[date].sort((a, b) => {
                                            const order = { 'breakfast': 1, 'lunch': 2, 'snack': 3, 'dinner': 4 };
                                            return (order[a.meal_type] || 99) - (order[b.meal_type] || 99);
                                        }).map((meal, idx) => (
                                            <MenuCard key={`p-${date}-${idx}`} meal={meal} />
                                        ))}
                                    </div>
                                ))}
                                <hr className="divider" />
                            </div>
                        )}

                        {menu.confirmed.length > 0 && (
                            <div className="confirmed-section">
                                <h2>{text.todaysMenu}</h2>
                                {menu.confirmed.map((meal, idx) => (
                                    <MenuCard key={`c-${idx}`} meal={meal} />
                                ))}
                            </div>
                        )}
                    </>
                ) : (
                    <div className="empty-state">
                        <Clock size={48} />
                        <p>{text.noMeals}</p>
                        <p className="sub">{text.askToPlan}</p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default Dashboard;
