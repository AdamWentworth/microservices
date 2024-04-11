import React, { useEffect, useState } from 'react';
import '../App.css';

export default function EndpointAudit(props) {
    const [isLoaded, setIsLoaded] = useState(false);
    const [log, setLog] = useState(null);
    const [error, setError] = useState(null);
    const [index, setIndex] = useState(null); // Added state for index

    useEffect(() => {
        const getAudit = () => {
            const rand_val = Math.floor(Math.random() * 100); // Moved inside useEffect
            fetch(`http://kafka-3855.westus3.cloudapp.azure.com/audit/${props.endpoint}?index=${rand_val}`)
                .then(res => res.json())
                .then(
                    (result) => {
                        console.log("Received Audit Results for " + props.endpoint);
                        setLog(result);
                        setIndex(rand_val); // Set index state here
                        setIsLoaded(true);
                    },
                    (error) => {
                        setError(error);
                        setIsLoaded(true);
                    }
                );
        };

        const interval = setInterval(getAudit, 4000); // Refresh the fetched audit event every 4 seconds
        return () => clearInterval(interval);
    }, [props.endpoint]); // Removed rand_val from dependencies

    if (error) {
        return (<div className={"error"}>Error: {error.message}</div>);
    } else if (!isLoaded) {
        return (<div>Loading...</div>);
    } else {
        return (
            <div>
                <h3>{props.endpoint.toUpperCase()} Event {index}</h3> {/* Displaying the stateful index */}
                <div className="log-display">
                    {log ? Object.keys(log).map((key) => (
                        <p key={key}><strong>{key}:</strong> {JSON.stringify(log[key], null, 2)}</p>
                    )) : <p>No data found for this event.</p>}
                </div>
            </div>
        );
    }
}
