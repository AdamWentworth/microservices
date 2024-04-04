import React, { useEffect, useState } from 'react';
import '../App.css';

export default function EndpointAudit(props) {
    const [isLoaded, setIsLoaded] = useState(false);
    const [log, setLog] = useState(null);
    const [error, setError] = useState(null);
    const rand_val = Math.floor(Math.random() * 100); // Get a random event from the event store

    useEffect(() => {
        const getAudit = () => {
            // Ensure you replace "your-audit-service-dns" with the actual DNS name or IP address of your service
            fetch(`http://kafka-3855.westus3.cloudapp.azure.com:8110/${props.endpoint}?index=${rand_val}`)
                .then(res => res.json())
                .then(
                    (result) => {
                        console.log("Received Audit Results for " + props.endpoint);
                        setLog(result);
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
    }, [props.endpoint, rand_val]); // Adding props.endpoint and rand_val to useEffect dependencies

    if (error) {
        return (<div className={"error"}>Error: {error.message}</div>);
    } else if (!isLoaded) {
        return (<div>Loading...</div>);
    } else {
        return (
            <div>
                <h3>{props.endpoint.toUpperCase()} Event {rand_val}</h3>
                <div className="log-display">
                    {log ? Object.keys(log).map((key) => (
                        <p key={key}><strong>{key}:</strong> {JSON.stringify(log[key], null, 2)}</p>
                    )) : <p>No data found for this event.</p>}
                </div>
            </div>
        );
    }
}