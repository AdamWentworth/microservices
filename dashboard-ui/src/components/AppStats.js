import React, { useEffect, useState } from 'react'
import '../App.css';

export default function AppStats() {
    const [isLoaded, setIsLoaded] = useState(false);
    const [stats, setStats] = useState({});
    const [error, setError] = useState(null);

    const getStats = () => {
        // Update this URL to match your Processing Service's actual endpoint
        fetch(`http://kafka-3855.westus3.cloudapp.azure.com/processing/stats`)
            .then(res => res.json())
            .then((result) => {
                console.log("Received Stats");
                setStats(result);
                setIsLoaded(true);
            }, (error) => {
                setError(error);
                setIsLoaded(true);
            });
    }

    useEffect(() => {
        const interval = setInterval(() => getStats(), 2000); // Update every 2 seconds
        return () => clearInterval(interval);
    }, []);

    if (error) {
        return (<div className={"error"}>Error found when fetching from API</div>);
    } else if (!isLoaded) {
        return (<div>Loading...</div>);
    } else {
        return (
            <div>
                <h1>Latest Stats</h1>
                <table className={"StatsTable"}>
                    <tbody>
                        <tr>
                            <th>Total Artists</th>
                            <th>Max Followers</th>
                            <th>Max Spins</th>
                            <th>Number of Tracked Artists</th>
                        </tr>
                        <tr>
                            <td>{stats.total_artists}</td>
                            <td>{stats.max_followers}</td>
                            <td>{stats.max_spins}</td>
                            <td>{stats.number_of_tracked_artists}</td>
                        </tr>
                    </tbody>
                </table>
                <h3>Last Updated: {stats.last_updated}</h3>
            </div>
        );
    }
}
