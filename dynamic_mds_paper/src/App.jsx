import { useState } from 'react'
import './App.css'

function App() {
  const [model, setModel] = useState("baseline");
  const [karyotype, setKaryotype] = useState("0");
  const [age, setAge] = useState("");
  const [gender, setGender] = useState("m");
  const [blasts, setBlasts] = useState("");
  const [fileData, setFileData] = useState([]);
  const [csvString, setCsvString] = useState("");

  const handleCsvUpload = (e) => {
  const file = e.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = (evt) => {
    const text = evt.target.result;
    const lines = text.trim().split("\n");
    const header = lines[0].split(",").map(h => h.trim());

    const expectedHeader = [
      "day_from_diagnosis",
      "Leukozyten",
      "Erythrozyten",
      "Hämatokrit",
      "Thrombozyten",
      "Hämoglobin"
    ];

    const isValidHeader = expectedHeader.every((val, idx) => val === header[idx]);

    if (!isValidHeader) {
      alert("Invalid CSV header. Please upload a file with the correct columns:\n" + expectedHeader.join(", "));
      return;
    }

    setCsvString(text); // valid CSV, keep full content
    const rows = lines.slice(1, 21).map(line => {
      const values = line.split(",");
      return Object.fromEntries(header.map((h, i) => [h, values[i]]));
    });
    setFileData(rows);
  };

  reader.readAsText(file);
};

  const handleSubmit = async (e) => {
    e.preventDefault();
    const formData = {
      model,
      karyotype: parseInt(karyotype),
      age: parseFloat(age),
      gender,
      blasts: parseFloat(blasts),
      csv: csvString,
    };
    console.log(formData);
    // Send to FastAPI backend here
  };

  return (
    <div className="min-h-screen grid grid-cols-2 gap-4 p-6 bg-gray-100">
      {/* Left Column: Form */}
      <form className="space-y-4 bg-white p-6 rounded shadow" onSubmit={handleSubmit}>
        <h1 className="text-xl font-bold mb-4">Patient Data Input</h1>

        <div>
          <label className="block text-sm font-medium">Model</label>
          <select value={model} onChange={(e) => setModel(e.target.value)} className="w-full mt-1 p-2 border rounded">
            <option value="baseline">Baseline</option>
            <option value="longitudinal">Longitudinal</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium">Bone-Marrow Blasts %</label>
          <input type="number" step="0.1" value={blasts} onChange={(e) => setBlasts(e.target.value)} className="w-full mt-1 p-2 border rounded" />
        </div>

        <div>
          <label className="block text-sm font-medium">IPSSR Karyotype Classification (0-4)</label>
          <select value={karyotype} onChange={(e) => setKaryotype(e.target.value)} className="w-full mt-1 p-2 border rounded">
            {[0, 1, 2, 3, 4].map(i => <option key={i} value={i}>{i}</option>)}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium">Age</label>
          <input type="number" step="1" value={age} onChange={(e) => setAge(e.target.value)} className="w-full mt-1 p-2 border rounded" />
        </div>

        <div>
          <label className="block text-sm font-medium">Gender</label>
          <select value={gender} onChange={(e) => setGender(e.target.value)} className="w-full mt-1 p-2 border rounded">
            <option value="m">Male</option>
            <option value="f">Female</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium">Upload CSV</label>
          <input type="file" accept=".csv" onChange={handleCsvUpload} className="mt-1" />
        </div>

        {fileData.length > 0 && (
          <div className="overflow-x-auto mt-4 border">
            <table className="min-w-full text-sm text-left">
              <thead className="bg-gray-200">
                <tr>
                  {Object.keys(fileData[0]).map((key) => (
                    <th key={key} className="p-2">{key}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {fileData.map((row, idx) => (
                  <tr key={idx} className="border-t">
                    {Object.values(row).map((val, i) => (
                      <td key={i} className="p-2">{val}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">Submit</button>
      </form>

      {/* Right Column: Placeholder */}
      <div className="bg-white rounded shadow p-6">
        <h2 className="text-xl font-semibold text-gray-700">Results / Output (placeholder)</h2>
      </div>
    </div>
  );
}

export default App
