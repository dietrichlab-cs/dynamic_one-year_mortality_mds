import React, {useState} from 'react';

function CsvDropZone({onFileAccepted}) {
    const [isDragOver, setIsDragOver] = useState(false);
    const [showCsvHelp, setShowCsvHelp] = useState(false);

    const handleDrop = (e) => {
        e.preventDefault();
        setIsDragOver(false);

        const file = e.dataTransfer.files?.[0];
        if (file && file.name.endsWith(".csv")) {
            onFileAccepted(file);
        } else {
            alert("Please upload a .csv file");
        }
    };

    const handleDragOver = (e) => {
        e.preventDefault();
        setIsDragOver(true);
    };

    const handleDragLeave = () => setIsDragOver(false);

    const handleFileChange = (e) => {
        const file = e.target.files?.[0];
        if (file) onFileAccepted(file);
    };

    return (
        <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            className={`w-full p-6 border-2 border-dashed rounded-md transition-colors
        ${isDragOver ? "border-blue-500 bg-blue-50" : "border-gray-300 bg-white"}`}
        >
            <div className="mb-4 p-4 border rounded bg-gray-50 text-sm text-gray-700 shadow">
                <p className="font-medium mb-1">Expected CSV format/columns:<br/>Each row corresponds to a day of measurements. ONLY input one measurement per day.<br/>The file should include a header with the below column names.</p>
                <ul className="list-disc list-inside">
                    <li><code>day_from_diagnosis</code>: integer, measurement day offset from diagnosis day</li>
                    <li><code>leukocytes</code>: float, unit x1000/μl</li>
                    <li><code>erythrocytes</code>: float, unit Mio/μl</li>
                    <li><code>thrombocytes</code>: float, unit x1000/μl</li>
                    <li><code>hematocrit</code>: float, unit g/dl</li>
                </ul>
                <p className="mt-2">The first row should contain column headers.</p>
            </div>

            <div className="text-center text-gray-500">
                <p>Drag and drop a .csv file here, or click to browse</p>
                <input
                    type="file"
                    accept=".csv"
                    onChange={handleFileChange}
                    className="hidden"
                    id="file-upload"
                />
                <label
                    htmlFor="file-upload"
                    className="mt-2 inline-block px-4 py-2 bg-blue-600 text-white rounded cursor-pointer hover:bg-blue-700"
                >
                    Browse File
                </label>
            </div>
        </div>
    );
}

export default CsvDropZone;