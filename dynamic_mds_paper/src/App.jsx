import {useState} from 'react'
import './App.css'
import CsvDropZone from "./components/CsvDropZone.jsx";

function App() {
    const [model, setModel] = useState("longitudinal");
    const [karyotype, setKaryotype] = useState("");
    const [age, setAge] = useState("");
    const [gender, setGender] = useState("m");
    const [blasts, setBlasts] = useState("");
    const [fileData, setFileData] = useState([]);
    const [csvString, setCsvString] = useState("");
    const [easix, setEasix] = useState("");

    const [uploadedFile, setUploadedFile] = useState(null);
    const [errors, setErrors] = useState({});

    const karyotypeOptions = {
      0: "0 - Very Low",
      1: "1 - Low",
      2: "2 - Intermediate",
      3: "3 - High",
      4: "4 - Very High",
    };

    const handleCsvUpload = (e) => {
        const file = e.target.files?.[0];
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
                alert("Invalid CSV header.");
                return;
            }

            setCsvString(text);
            setUploadedFile(file); // ✅ mark that file is uploaded

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
        const newErrors = {};
        if (!age) newErrors.age = "Age is required";
        if (!gender) newErrors.gender = "Gender is required";
        if (!model) newErrors.model = "Model is required";
        if (!csvString.trim()) newErrors.csv = "CSV data is required";

        if (Object.keys(newErrors).length > 0) {
            setErrors(newErrors);
            return;
        }

        setErrors({});  // Clear previous errors

        const formData = {
            model,
            karyotype: karyotype === "" ? null : parseInt(karyotype),
            age: parseFloat(age),
            gender,
            blasts: parseFloat(blasts),
            csv: csvString,
            easix: easix ? parseFloat(easix) : null,
            ...(model === "baseline" && easix !== "" && {easix: parseFloat(easix)}),
        };

        try {
            const response = await fetch("http://localhost:8000/predict", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(formData),
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail);
            }

            const data = await response.json();
            console.log("Predictions:", data.predictions);
        } catch (error) {
            console.error("Prediction failed:", error);
            alert("Prediction failed: " + error.message);
        }
    };

    return (
        <div className="min-h-screen w-full grid grid-cols-3 gap-4 p-6 bg-gray-100">
            {/* Left Column: Form */}
            <form className="col-span-2 w-full grid grid-cols-20 space-y-4 bg-white py-6 ps-6 pe-1 rounded shadow"
                  onSubmit={handleSubmit}>
                {/* Form fields go here */}
                <div className="space-y-4 col-span-19">
                    {/* All your inputs/selects/upload etc */}
                    <h2 className="text-xl font-bold mb-4">Patient Data Input</h2>
                    <p>Fields marked with * are always required</p>

                    <div>
                        <label className="block font-medium">Model *</label>
                        <select value={model} onChange={(e) => setModel(e.target.value)}
                                className="w-full mt-1 p-2 border rounded">
                            <option value="baseline">Baseline</option>
                            <option value="longitudinal">Longitudinal</option>
                        </select>
                        {errors.model && <p className="text-red-500 text-sm mt-1">{errors.model}</p>}
                    </div>

                    <div>
                        <label className="block font-medium">Bone-Marrow Blasts %</label>
                        <input type="number" step="0.1" min="0" max="100" value={blasts}
                               onChange={(e) => setBlasts(e.target.value)} className="w-full mt-1 p-2 border rounded"/>
                    </div>

                    <div>
                        <label className="block font-medium">IPSSR Karyotype Classification (0-4)</label>
                        <select value={karyotype} onChange={(e) => setKaryotype(e.target.value)}
                                className="w-full mt-1 p-2 border rounded">
                            <option value="">-- Select --</option>
                            {Object.entries(karyotypeOptions).map(([value, label]) => (
                              <option key={value} value={value}>{label}</option>
                            ))}
                        </select>
                    </div>

                    <div>
                        <label className="block font-medium">Age *</label>
                        <input type="number" step="1" min="0" value={age} onChange={(e) => setAge(e.target.value)}
                               className="w-full mt-1 p-2 border rounded"/>
                        {errors.age && <p className="text-red-500 text-sm mt-1">{errors.age}</p>}
                    </div>

                    <div>
                        <label className="block font-medium">Gender *</label>
                        <select value={gender} onChange={(e) => setGender(e.target.value)}
                                className="w-full mt-1 p-2 border rounded">
                            <option value="m">Male</option>
                            <option value="f">Female</option>
                        </select>
                        {errors.gender && <p className="text-red-500 text-sm mt-1">{errors.gender}</p>}
                    </div>
                    {model === "baseline" && (
                        <div>
                            <label className="block font-medium">EASIX Score</label>
                            <input type="number" step="0.5" min="0" value={easix}
                                   onChange={(e) => setEasix(e.target.value)}
                                   className="w-full mt-1 p-2 border rounded"/>
                        </div>
                    )}
                    {uploadedFile ? (
                        <div className="mt-4 space-y-2">
                            <p className="text-sm text-gray-600">Uploaded: {uploadedFile.name}</p>
                            <button
                                type="button"
                                onClick={() => {
                                    setUploadedFile(null);
                                    setFileData([]);
                                    setCsvString("");
                                }}
                                className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
                            >
                                Clear File
                            </button>
                        </div>
                    ) : (
                        <CsvDropZone onFileAccepted={(file) => handleCsvUpload({target: {files: [file]}})}/>
                    )}
                    {errors.csv && <p className="text-red-500 text-sm mt-1">{errors.csv}</p>}

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
                </div>
                {/* Submit button: vertical, rotated text */}
                <div className="col-span-1 flex justify-center ms-2 p-5">
                    <button
                        type="submit"
                        className="w-full h-full bg-blue-600 text-white rounded hover:bg-blue-700 flex items-center justify-center"
                    >
             <span className="transform -rotate-90 origin-center whitespace-nowrap tracking-wider">
               Predict
             </span>
                    </button>
                </div>
            </form>
        </div>
    );
}

export default App
