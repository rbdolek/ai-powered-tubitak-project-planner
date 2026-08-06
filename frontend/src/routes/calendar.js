import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';

const Calendar = () => {
    const navigate = useNavigate();
    const [currentDate, setCurrentDate] = useState(new Date());
    const [currentView, setCurrentView] = useState('month');
    const [projectCalendars, setProjectCalendars] = useState({});
    const [selectedCalendar, setSelectedCalendar] = useState(null);
    const [calendarData, setCalendarData] = useState(null);
    const [selectedTask, setSelectedTask] = useState(null);
    const modalRef = useRef(null);

    useEffect(() => {
        // Load calendars from localStorage
        try {
            const savedCalendarsJson = localStorage.getItem('projectCalendars');
            if (savedCalendarsJson) {
                const savedCalendars = JSON.parse(savedCalendarsJson);

                // Convert string dates to Date objects
                Object.values(savedCalendars).forEach(calendar => {
                    calendar.startDate = new Date(calendar.startDate);
                    calendar.endDate = new Date(calendar.endDate);
                });

                setProjectCalendars(savedCalendars);

                // If there's at least one calendar, select the first one
                const calendarIds = Object.keys(savedCalendars);
                if (calendarIds.length > 0 && !selectedCalendar) {
                    setSelectedCalendar(calendarIds[0]);
                }
            }
        } catch (e) {
            console.error('Calendars could not be loaded:', e);
        }
    }, [selectedCalendar]);

    useEffect(() => {
        // When selectedCalendar changes, update calendarData
        if (selectedCalendar && projectCalendars[selectedCalendar]) {
            setCalendarData(projectCalendars[selectedCalendar]);
        }
    }, [selectedCalendar, projectCalendars]);

    // Click outside modal to close it
    useEffect(() => {
        function handleClickOutside(event) {
            if (modalRef.current && !modalRef.current.contains(event.target)) {
                setSelectedTask(null);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => {
            document.removeEventListener("mousedown", handleClickOutside);
        };
    }, [modalRef]);

    const goToToday = () => {
        setCurrentDate(new Date());
    };

    const goToPrevious = () => {
        const newDate = new Date(currentDate);
        if (currentView === 'month') {
            newDate.setMonth(newDate.getMonth() - 1);
        } else if (currentView === 'week') {
            newDate.setDate(newDate.getDate() - 7);
        } else {
            newDate.setDate(newDate.getDate() - 1);
        }
        setCurrentDate(newDate);
    };

    const goToNext = () => {
        const newDate = new Date(currentDate);
        if (currentView === 'month') {
            newDate.setMonth(newDate.getMonth() + 1);
        } else if (currentView === 'week') {
            newDate.setDate(newDate.getDate() + 7);
        } else {
            newDate.setDate(newDate.getDate() + 1);
        }
        setCurrentDate(newDate);
    };

    // Seçili projeyi silme fonksiyonu
    const deleteSelectedProject = () => {
        if (!selectedCalendar) {
            alert('Lütfen silmek için bir proje seçin.');
            return;
        }

        if (window.confirm('Seçili projeyi silmek istediğinizden emin misiniz? Bu işlem geri alınamaz.')) {
            try {
                // localStorage'dan mevcut projeleri al
                const savedCalendarsJson = localStorage.getItem('projectCalendars');
                if (savedCalendarsJson) {
                    const savedCalendars = JSON.parse(savedCalendarsJson);

                    // Seçili projeyi sil
                    delete savedCalendars[selectedCalendar];

                    // Güncellenmiş projeleri localStorage'a kaydet
                    localStorage.setItem('projectCalendars', JSON.stringify(savedCalendars));

                    // State'i güncelle
                    setProjectCalendars(savedCalendars);
                    setSelectedCalendar(null);
                    setCalendarData(null);

                    alert('Proje başarıyla silindi.');
                }
            } catch (e) {
                console.error('Proje silinirken hata oluştu:', e);
                alert('Proje silinirken bir hata oluştu.');
            }
        }
    };

    // Tüm projeleri temizleme fonksiyonu
    const clearAllProjects = () => {
        if (window.confirm('Tüm projeleri silmek istediğinizden emin misiniz? Bu işlem geri alınamaz.')) {
            localStorage.removeItem('projectCalendars');
            setProjectCalendars({});
            setSelectedCalendar(null);
            setCalendarData(null);
            alert('Tüm projeler başarıyla silindi.');
        }
    };

    // Create calendar grid
    const renderMonthCalendar = () => {
        if (!calendarData) return [];

        const monthStart = new Date(currentDate.getFullYear(), currentDate.getMonth(), 1);
        const monthEnd = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 0);
        const startDate = new Date(monthStart);

        // Start from Monday (adjust first day of week)
        startDate.setDate(startDate.getDate() - (startDate.getDay() === 0 ? 6 : startDate.getDay() - 1));

        const endDate = new Date(monthEnd);
        if (endDate.getDay() !== 0) {
            endDate.setDate(endDate.getDate() + (7 - endDate.getDay()));
        }

        const weeks = [];
        let days = [];

        // Calculate project start and end dates
        const projectStartDate = new Date(calendarData.startDate);
        const projectEndDate = new Date(calendarData.endDate);

        // Generate days
        for (let day = new Date(startDate); day <= endDate; day.setDate(day.getDate() + 1)) {
            const clonedDate = new Date(day);

            // Find tasks for this day
            const tasks = [];

            // Check if this day is within project timeline
            if (clonedDate >= projectStartDate && clonedDate <= projectEndDate) {
                // Calculate which month of the project this day belongs to
                const dayDiff = Math.floor((clonedDate - projectStartDate) / (1000 * 60 * 60 * 24));
                const monthIndex = Math.floor(dayDiff / 30); // Approximate month calculation

                if (calendarData.months && monthIndex >= 0 && monthIndex < calendarData.months.length) {
                    const monthData = calendarData.months[monthIndex];

                    // If it's the first day of a project month, add month title
                    if (dayDiff % 30 === 0) {
                        tasks.push({
                            id: `month-${monthIndex}`,
                            title: `Ay ${monthData.month}: ${monthData.title}`,
                            type: 'month-title',
                            color: '#4285f4', // Blue
                            monthData: monthData
                        });
                    }

                    // Distribute tasks throughout the month
                    const dayOfMonth = dayDiff % 30;

                    if (monthData.tasks && monthData.tasks.length > 0) {
                        // Spread tasks evenly across the month
                        const taskIndex = Math.floor((dayOfMonth / 30) * monthData.tasks.length);
                        if (taskIndex < monthData.tasks.length && dayOfMonth % 3 === 0) {
                            tasks.push({
                                id: `task-${monthIndex}-${taskIndex}`,
                                title: monthData.tasks[taskIndex],
                                type: 'task',
                                color: '#0f9d58', // Green
                                monthData: monthData
                            });
                        }
                    }
                }
            }

            days.push({
                date: clonedDate,
                isCurrentMonth: clonedDate.getMonth() === currentDate.getMonth(),
                isToday: clonedDate.toDateString() === new Date().toDateString(),
                tasks: tasks
            });

            if (days.length === 7) {
                weeks.push([...days]);
                days = [];
            }
        }

        return weeks;
    };

    // Handle task click to show details
    const handleTaskClick = (task) => {
        setSelectedTask(task);
    };

    // Return to main page
    const handleReturn = () => {
        navigate('/');
    };

    // Calendar title (Month Year)
    const getCalendarTitle = () => {
        const months = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık'];
        return `${months[currentDate.getMonth()]} ${currentDate.getFullYear()}`;
    };

    // Weekday headers
    const weekDays = ['Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz'];

    return (
        <div style={{
            fontFamily: "'Poppins', sans-serif",
            backgroundColor: '#1c1c1c',
            color: 'white',
            minHeight: '100vh',
            padding: '20px'
        }}>
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '20px',
                flexWrap: 'wrap'
            }}>
                <h1 style={{ margin: 0 }}>Proje Takvimi</h1>

                <div style={{
                    display: 'flex',
                    gap: '10px',
                    flexWrap: 'wrap',
                    marginTop: '10px'
                }}>
                    <button
                        onClick={goToToday}
                        style={{
                            backgroundColor: '#e30613',
                            color: 'white',
                            border: 'none',
                            borderRadius: '4px',
                            padding: '8px 15px',
                            cursor: 'pointer'
                        }}
                    >
                        Bugün
                    </button>
                    <button
                        onClick={goToPrevious}
                        style={{
                            backgroundColor: '#333',
                            color: 'white',
                            border: 'none',
                            borderRadius: '4px',
                            padding: '8px 15px',
                            cursor: 'pointer'
                        }}
                    >
                        &lt;
                    </button>
                    <button
                        onClick={goToNext}
                        style={{
                            backgroundColor: '#333',
                            color: 'white',
                            border: 'none',
                            borderRadius: '4px',
                            padding: '8px 15px',
                            cursor: 'pointer'
                        }}
                    >
                        &gt;
                    </button>
                    <div style={{
                        backgroundColor: '#333',
                        color: 'white',
                        borderRadius: '4px',
                        padding: '8px 15px'
                    }}>
                        {getCalendarTitle()}
                    </div>
                </div>
            </div>

            {/* Project Selection with Delete Button */}
            <div style={{
                marginBottom: '20px',
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                flexWrap: 'wrap'
            }}>
                <select
                    value={selectedCalendar || ''}
                    onChange={(e) => setSelectedCalendar(e.target.value)}
                    style={{
                        backgroundColor: '#333',
                        color: 'white',
                        padding: '8px',
                        borderRadius: '4px',
                        border: '1px solid #444',
                        flexGrow: 1,
                        maxWidth: '500px',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis'
                    }}
                >
                    <option value="">Proje Seçin...</option>
                    {Object.entries(projectCalendars).map(([id, calendar]) => (
                        <option key={id} value={id}>
                            {calendar.fonCode} - {calendar.projectTitle}
                        </option>
                    ))}
                </select>

                <button
                    onClick={deleteSelectedProject}
                    style={{
                        backgroundColor: '#d32f2f',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        padding: '8px 15px',
                        cursor: 'pointer',
                        whiteSpace: 'nowrap'
                    }}
                >
                    Seçili Projeyi Sil
                </button>

                <button
                    onClick={clearAllProjects}
                    style={{
                        backgroundColor: '#d32f2f',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        padding: '8px 15px',
                        cursor: 'pointer',
                        whiteSpace: 'nowrap'
                    }}
                >
                    Tüm Projeleri Sil
                </button>
            </div>

            {/* Project Details */}
            {calendarData && (
                <div style={{
                    backgroundColor: '#333',
                    padding: '15px',
                    borderRadius: '8px',
                    marginBottom: '20px',
                    fontSize: '14px',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis'
                }}>
                    <div style={{ whiteSpace: 'normal', wordBreak: 'break-word' }}>
                        {calendarData.fonCode} - {calendarData.projectTitle} • Süre: {calendarData.duration} ay
                    </div>
                </div>
            )}

            {/* View Selection */}
            <div style={{
                display: 'flex',
                gap: '5px',
                marginBottom: '15px',
                flexWrap: 'wrap'
            }}>
                <button
                    onClick={() => setCurrentView('month')}
                    style={{
                        backgroundColor: currentView === 'month' ? '#e30613' : '#333',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        padding: '8px 15px',
                        cursor: 'pointer'
                    }}
                >
                    Ay
                </button>
                <button
                    onClick={() => setCurrentView('week')}
                    style={{
                        backgroundColor: currentView === 'week' ? '#e30613' : '#333',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        padding: '8px 15px',
                        cursor: 'pointer'
                    }}
                >
                    Hafta
                </button>
                <button
                    onClick={() => setCurrentView('day')}
                    style={{
                        backgroundColor: currentView === 'day' ? '#e30613' : '#333',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        padding: '8px 15px',
                        cursor: 'pointer'
                    }}
                >
                    Gün
                </button>
            </div>

            {calendarData ? (
                /* Calendar Grid */
                <div style={{
                    backgroundColor: '#333',
                    borderRadius: '8px',
                    overflow: 'hidden'
                }}>
                    {/* Day Headers */}
                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(7, 1fr)',
                        textAlign: 'center',
                        borderBottom: '1px solid #444'
                    }}>
                        {weekDays.map((day, index) => (
                            <div key={index} style={{
                                padding: '10px',
                                fontWeight: 'bold',
                                backgroundColor: '#2c2c2c'
                            }}>
                                {day}
                            </div>
                        ))}
                    </div>

                    {/* Calendar Days */}
                    <div>
                        {renderMonthCalendar().map((week, weekIndex) => (
                            <div key={weekIndex} style={{
                                display: 'grid',
                                gridTemplateColumns: 'repeat(7, 1fr)',
                            }}>
                                {week.map((day, dayIndex) => (
                                    <div key={dayIndex} style={{
                                        padding: '8px',
                                        minHeight: '120px',
                                        borderBottom: '1px solid #444',
                                        borderRight: dayIndex < 6 ? '1px solid #444' : 'none',
                                        backgroundColor: day.isCurrentMonth ? (day.isToday ? '#383838' : '#2a2a2a') : '#222',
                                        opacity: day.isCurrentMonth ? 1 : 0.5,
                                        position: 'relative'
                                    }}>
                                        <div style={{
                                            display: 'flex',
                                            justifyContent: 'center',
                                            alignItems: 'center',
                                            width: '24px',
                                            height: '24px',
                                            borderRadius: '50%',
                                            backgroundColor: day.isToday ? '#e30613' : 'transparent',
                                            margin: '0 auto 8px',
                                            fontWeight: day.isToday ? 'bold' : 'normal'
                                        }}>
                                            {day.date.getDate()}
                                        </div>

                                        {/* Tasks */}
                                        <div style={{
                                            display: 'flex',
                                            flexDirection: 'column',
                                            gap: '2px',
                                            fontSize: '12px'
                                        }}>
                                            {day.tasks.map((task) => (
                                                <div
                                                    key={task.id}
                                                    onClick={() => handleTaskClick(task)}
                                                    style={{
                                                        backgroundColor: task.color,
                                                        color: 'white',
                                                        padding: '4px 6px',
                                                        borderRadius: '3px',
                                                        overflow: 'hidden',
                                                        textOverflow: 'ellipsis',
                                                        whiteSpace: 'nowrap',
                                                        cursor: 'pointer',
                                                        transition: 'transform 0.2s',
                                                        ':hover': {
                                                            transform: 'scale(1.02)'
                                                        }
                                                    }}
                                                >
                                                    {task.title}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ))}
                    </div>
                </div>
            ) : (
                <div style={{
                    backgroundColor: '#333',
                    padding: '20px',
                    borderRadius: '8px',
                    textAlign: 'center'
                }}>
                    <p>Lütfen bir proje seçin veya plan sayfasında takvim oluşturun.</p>
                </div>
            )}

            {/* Return Button */}
            <div style={{
                marginTop: '20px',
                display: 'flex',
                justifyContent: 'center'
            }}>
                <button
                    onClick={handleReturn}
                    style={{
                        backgroundColor: '#444',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        padding: '10px 20px',
                        cursor: 'pointer'
                    }}
                >
                    Ana Sayfaya Dön
                </button>
            </div>

            {/* Task Detail Modal */}
            {selectedTask && (
                <div style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    backgroundColor: 'rgba(0,0,0,0.7)',
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                    zIndex: 100
                }}>
                    <div
                        ref={modalRef}
                        style={{
                            backgroundColor: '#333',
                            borderRadius: '8px',
                            padding: '20px',
                            maxWidth: '400px',
                            width: '90%',
                            maxHeight: '80vh',
                            overflow: 'auto',
                            position: 'relative',
                            border: `2px solid ${selectedTask.color}`
                        }}
                    >
                        <button
                            onClick={() => setSelectedTask(null)}
                            style={{
                                position: 'absolute',
                                top: '10px',
                                right: '10px',
                                backgroundColor: 'transparent',
                                border: 'none',
                                color: '#aaa',
                                fontSize: '20px',
                                cursor: 'pointer'
                            }}
                        >
                            ×
                        </button>

                        <h3 style={{ color: selectedTask.color, marginTop: 0 }}>
                            {selectedTask.type === 'month-title'
                                ? `Ay ${selectedTask.monthData.month}: ${selectedTask.monthData.title}`
                                : selectedTask.title
                            }
                        </h3>

                        {selectedTask.type === 'month-title' && selectedTask.monthData.tasks && (
                            <div>
                                <h4>Bu ay için planlanan görevler:</h4>
                                <ul style={{ paddingLeft: '20px' }}>
                                    {selectedTask.monthData.tasks.map((task, index) => (
                                        <li key={index} style={{ marginBottom: '5px' }}>{task}</li>
                                    ))}
                                </ul>
                            </div>
                        )}

                        {selectedTask.type === 'task' && (
                            <div>
                                <p><strong>Ay:</strong> {selectedTask.monthData.month}</p>
                                <p><strong>Ay Başlığı:</strong> {selectedTask.monthData.title}</p>
                                <p><strong>Görev:</strong> {selectedTask.title}</p>
                            </div>
                        )}

                        <div style={{
                            marginTop: '20px',
                            display: 'flex',
                            justifyContent: 'flex-end'
                        }}>
                            <button
                                onClick={() => setSelectedTask(null)}
                                style={{
                                    backgroundColor: '#555',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '4px',
                                    padding: '8px 15px',
                                    cursor: 'pointer'
                                }}
                            >
                                Kapat
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Calendar;