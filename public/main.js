/**
 * Use Handlebar templates to generate HTML.
 */

const familyJsonDivSize = 100;
const personJsonDivSize = 1000;
const factsJsonDivSize = 1000;


/**
 * Fetches a JSON file and passes it to the callback function.
 *
 * @param {string} fileURL - URL to JSON file.
 * @param {textCallback} callback - Callback function that handles the response. If not specified
 *      then the request won't happen asynchronously and will only return once completed.
 */
function readJsonFile(fileURL, callback, errorCallback=Function()) {
    var rawFile = new XMLHttpRequest();
    rawFile.overrideMimeType("application/json");
    if (callback) {
        rawFile.onreadystatechange = function() {
            if (rawFile.readyState === 4) {
                if (rawFile.status == "200") {
                    callback(rawFile.responseText);
                } else {
                    errorCallback(rawFile);
                 }
            }
        }
    }
    // set to be synchronous if no callback is provided
    rawFile.open("GET", fileURL, !(!callback));
    rawFile.send(null);
    return rawFile;
}


/**
 * Determine the filename of a divided-JSON file (i.e. a dictionary where the keys are
 * integer ids that have been split across multiple files).
 */
function divJsonFilenameFromId(prepend, id, divisions=1000) {
    // E.g. files with name "1000-2000" contain ids 1000 to 1999 (inclusive)
    lower = Math.floor(id / divisions) * divisions;
    upper = lower + divisions;
    return `${prepend}-${lower}-${upper}.json`;
}


function loadRelativeData(familyLinks) {
    var relativeData = {};
    familyLinks.forEach(link => {
        const familyId = link[0];
        const roleType = link[1];
        const familyType = isChild(roleType) ? 'ischild' : 'isparent';
        const req = readJsonFile(divJsonFilenameFromId("json/families/families", familyId, familyJsonDivSize));
        if (req.status == 200) {
            const jsonData = JSON.parse(req.response);
            const familyData = jsonData[familyId];
            if (relativeData.hasOwnProperty(familyType)) {
                relativeData[familyType].push(familyData)
            } else {
                relativeData[familyType] = [familyData];
            }
        }
    });
    // sort parent with husband first (without affecting child order?)
    if (relativeData.hasOwnProperty('ischild')) {
        relativeData['ischild'].forEach(family => {
            family.members.sort((m1, m2) => m1.roleType > m2.roleType);
        });
    }
    return relativeData;
}


function processPersonData(personId, personDiv, response) {
    var personData = { 'personId': personId };
    const jsonData = JSON.parse(response);

    if (!jsonData.hasOwnProperty(personId)) {
        personDiv.innerHTML = `<span>Missing person data for ${personId}</span>`;
        return;
    }

    personData = jsonData[personId];
    personDiv.innerHTML = htmlPerson(personData);

    const factsUl = document.getElementById("person-facts");
    readJsonFile(divJsonFilenameFromId("json/facts/facts", personId, factsJsonDivSize), function(text){
        const facts = JSON.parse(text);
        const personFacts = facts[personId];
        console.log('Facts', facts[personId]);
        factsUl.innerHTML += htmlPersonFacts(personFacts);
    });
}


function processFamilyLinks(personId, relativesDiv, response) {
    var familyLinks = JSON.parse(response);
    // take metadata and show in footer
    if (familyLinks.hasOwnProperty("metadata")) {
        const metadata = familyLinks["metadata"];
        footer.innerHTML = `Generated at ${metadata["generated_at"].replace("T", " ")}`
            + `<br/> from data updated at ${metadata["source_updated_at"].replace("T", " ")}`;
    }
    // check if response contains relevant data
    if (!familyLinks.hasOwnProperty(personId)) {
        console.log('No family data for', personId);
        relativesDiv.innerHTML = `<span>No family data for ${personId}</span>`;
        return;
    }

    console.log('Family links', familyLinks[personId]);
    var relativeData = loadRelativeData(familyLinks[personId]);

    // show relatives in html only
    // relativesDiv.innerHTML = htmlRelatives(personId, relativeData);

    // show relative trees
    const [chart_config, child_count] = treeRelatives(personId, relativeData);
    var height = 40 + 90*child_count;
    relativesDiv.innerHTML = `
    <h3>Parents/siblings</h3>
    <div id="parent-tree" style="width: 500px; height: ${height}px"></div>
    <h3>Spouses/partners/children</h3>
    <div id="spouse-tree"></div>
    `;
    const chart = new Treant(chart_config);
};


function loadFamilyTree(personId) {
    personId = parseInt(personId);

    const personDiv = document.getElementById("person-details");
    const relativesDiv = document.getElementById("relatives");
    const footer = document.getElementById("footer");

    document.title = `Family tree: ${personId}`;

    personDiv.classList.add('loading');
    readJsonFile(divJsonFilenameFromId("json/people/people", personId, personJsonDivSize), function(response) {
        processPersonData(personId, personDiv, response);
        personDiv.classList.remove('loading');
    }, function(response) {
        personDiv.innerHTML = `Unknown person: ${personId}`;
        personDiv.classList.remove('loading');
    });

    relativesDiv.classList.add('loading');
    readJsonFile("json/family-links.json", function(response) {
        processFamilyLinks(personId, relativesDiv, response);
        relativesDiv.classList.remove('loading');
    });
}


function jumpToPerson(value) {
    if (value) {
        window.location.hash = `#${value}`;
    }
}


function loadQuickJump() {
    readJsonFile("json/person-search.json", function(text){
        var personSearch = JSON.parse(text);

        const select = document.getElementById('jump-to-person');
        personSearch.forEach(person => {
            select.add(new Option(person[1], person[0]));
        });
        new TomSelect("#jump-to-person", {
            onChange: function(value){ 
                jumpToPerson(value);
                this.clear();
            }
        });
        const header = document.getElementsByTagName("header")[0];
        header.classList.remove("hidden");
    });
}


function main() {
    loadQuickJump();

    if (window.location.hash.length == 0) {
        // Set a default person to start with
        window.location.hash = '#19';
    } else {
        // Perform initial load since it isn't triggered by URL change
        loadFamilyTree(window.location.hash.substring(1));
    }
}


window.addEventListener('DOMContentLoaded', main, false);

// Detect changes in URL hash and reload family tree data 
window.addEventListener('hashchange',() => {
    loadFamilyTree(window.location.hash.substring(1));
});
