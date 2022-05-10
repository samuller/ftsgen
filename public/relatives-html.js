/**
 * Use Handlebar templates to generate HTML describing person and their relatives.
 */


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
        {{#each ischild}}
        {{#each members}}
        {{#if (isParent this.roleType)}}
        <td>{{{personLink this}}}</td>
        {{/if}}
        {{/each}}
        {{/each}}
    </tr>
    <tr>
        <th>Siblings:</th>
        {{#each ischild}}
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
        {{#each isparent}}
        {{#each members}}
        {{#if (isParent this.roleType)}}
        <td>{{{personLink this}}}</td>
        {{/if}}
        {{/each}}
        {{/each}}
    </tr>
    <tr>
        <th>Children:</th>
        {{#each isparent}}
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


function htmlRelatives(personId, relativeData) {
    removeSelfFromMembers(personId, relativeData);
    console.log("Family tree data", relativeData);
    return relativesTemplate({ relatives: relativeData });
}
