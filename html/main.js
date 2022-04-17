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
 * Determines if a person had a child role within a family, based on their roleType string.
 */
function isChild(roleType) {
    return roleType.includes("child");
}


Handlebars.registerHelper('json', function(context) {
    return JSON.stringify(context);
});

Handlebars.registerHelper('isParent', function (value) {
    return !isChild(value);
});

Handlebars.registerHelper('personLink', function (value) {
    const gender = this.gender == 'M' ? 'male' : this.gender == 'F' ? 'female' : '';
    return `<div class="person ${gender}">
        <a href="#${this.personId}"><span class="link-spanner"></span></a>
        ${this.firstName} ${this.lastName}
    </div>`;
});

Handlebars.registerHelper('gender', function (value) {
    return value == 'M' ? 'male' : value == 'F' ? 'female' : '';
});


Handlebars.registerHelper('age', function (value) {
    if (!value.facts.birth.date || !value.facts.death.date) {
        return '';
    }
    var birth = new Date(value.facts.birth.date);
    var death = new Date(value.facts.death.date);
    if (isNaN(birth) || isNaN(death)) {
        return '';
    }

    var ageDifMs = death - birth;
    var ageDate = new Date(ageDifMs); // miliseconds from epoch
    var age = Math.abs(ageDate.getUTCFullYear() - 1970);
    return `(${age})`
});


const personTemplate = Handlebars.compile(`
<h2>{{person.firstName}} {{person.lastName}} [{{person.personId}}]</h2>
<ul id="person-facts">
    <li>Gender: {{gender person.gender}}</li>
</ul>
`);

const personFactsTemplate = Handlebars.compile(`
{{#if facts}}
{{#each facts}}
<li><span style="text-transform: capitalize">{{type}}</span>:
    {{#if description}}
        {{description}}
        {{#if date}}
            on {{date}}
        {{/if}}
    {{else}}
        {{#if date}}
            {{date}}
        {{/if}}
    {{/if}}
    {{#if place}}
        at {{place}}
    {{/if}}
</li>
{{/each}}
{{/if}}
`);


const relativesTemplate = Handlebars.compile(`
<h3>Relatives</h3>
{{#with relatives}}
<table class="relatives">
    <tr>
        <th>Parents:</th>
        {{#each child}}
        {{#each members}}
        {{#if (isParent this.roleType)}}
        <td>{{{personLink this}}}</td>
        {{/if}}
        {{/each}}
        {{/each}}
    </tr>
    <tr>
        <th>Siblings:</th>
        {{#each child}}
        <td colspan="2">
        {{#each members}}
        {{#unless (isParent this.roleType)}}
        {{{personLink this}}}
        {{/unless}}
        {{/each}}
        </td>
        {{/each}}
    </tr>
    <tr>
        <th>Spouses/partners:</th>
        {{#each parent}}
        {{#each members}}
        {{#if (isParent this.roleType)}}
        <td>{{{personLink this}}}</td>
        {{/if}}
        {{/each}}
        {{/each}}
    </tr>
    <tr>
        <th>Children:</th>
        {{#each parent}}
        <td>
        {{#each members}}
        {{#unless (isParent this.roleType)}}
        {{{personLink this}}}
        {{/unless}}
        {{/each}}
        </td>
        {{/each}}
    </tr>
</table>
{{/with}}
`);


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
        const familyType = isChild(roleType) ? 'child' : 'parent';
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
    return relativeData;
}


function removeSelfFromMembers(selfId, relativeData) {
    Object.keys(relativeData).forEach(type => {
        relativeData[type].forEach(family => {
            const members = family['members'];
            const selfIdx = members.map(member => member['personId']).indexOf(selfId);
            if (selfIdx != -1) {
                members.splice(selfIdx, 1);
            }
        });
    });
}


function htmlPerson(personData) {
    return personTemplate({ person: personData });
}


function htmlPersonFacts(personFacts) {
    return personFactsTemplate({ facts: personFacts });
}


function htmlRelatives(personId, familyLinks) {
    var relativeData = loadRelativeData(familyLinks);
    removeSelfFromMembers(personId, relativeData);
    console.log("Family tree data", relativeData);
    return relativesTemplate({ relatives: relativeData });
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
    relativesDiv.innerHTML = htmlRelatives(personId, familyLinks[personId]);
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
