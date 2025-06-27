import React, { useState } from 'react';

function CsvDropZone({ onFileAccepted }) {
  const [isDragOver, setIsDragOver] = useState(false);

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
      <label className="block text-sm font-medium text-gray-700 mb-2">Upload CSV *</label>
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