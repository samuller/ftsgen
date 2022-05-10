function familyMemberToTreantNode(member) {
    return {
        text: { name: `${member.firstName} ${member.lastName}` },
        link: { href: `#${member.personId}` },
        HTMLclass: member.gender == "M" ? "tree-male" : (
            member.gender == "F" ? "tree-female" : ""),
    };
}


function treeRelatives(personId, relativeData) {
    // ignore other parent families (e.g. later adoptions, etc.)
    var mainFamily = relativeData.ischild[0];

    var nodes = [];
    const husband = mainFamily.members.find(el => el.roleType == "husband");
    nodes.push(familyMemberToTreantNode(husband));
    const children = mainFamily.members.filter(el => el.roleType.endsWith("child"));
    nodes.push({
        HTMLclass: "tree-rel-link",
        text: { name: "" },
        childrenDropLevel: 1,
        children: children.map((child) => {
            var newNode = familyMemberToTreantNode(child);
            if (child.personId == personId) {
                newNode.HTMLclass = "tree-main-person";
            }
            return newNode;
        })
    });
    const wife = mainFamily.members.find(el => el.roleType == "wife");
    nodes.push(familyMemberToTreantNode(wife));
    console.log('tree-nodes', nodes, relativeData)

    const chart_config = {
        chart: {
            container: "#parent-tree",
            rootOrientation: "WEST",
            connectors: {
                type: "step"
            },
            hideRootNode: true,
            node: {
                HTMLclass: "tree-dark-box"
            }
        },
        nodeStructure: {
            text: { name: "root" },
            children: nodes,
        }
    };
    var chart = new Treant(
		chart_config,
		function() { console.log( 'Tree Loaded' ) }
	);
}
